//! The desktop shell does five things: spawn the bundled harness, hand the renderer the harness
//! address and credential, run the native folder picker, send the owner's Pause and Cancel from
//! the menu straight to the harness, and provide a Quit menu that stops the harness it started.
//! Closing the window only detaches: the harness keeps running. Everything else is in the harness.

use std::{
    env, fs,
    path::{Path, PathBuf},
    process::Command,
    sync::{
        atomic::{AtomicBool, AtomicU64, Ordering},
        mpsc, Arc,
    },
    thread,
};

use serde_json::{json, Value};
use tauri::menu::{Menu, MenuItem, Submenu};

/// Where the harness publishes its port and owner-only token: `DSP_HOME`, or `~/.dsp`.
fn state_file() -> Option<PathBuf> {
    let home = env::var_os("DSP_HOME")
        .filter(|value| !value.is_empty())
        .map(PathBuf::from)
        .or_else(|| env::home_dir().map(|home| home.join(".dsp")))?;
    Some(home.join("harness.json"))
}

/// The running harness's base URL and bearer token, read fresh on every call.
#[tauri::command]
fn harness() -> Result<Value, String> {
    let text = fs::read_to_string(state_file().ok_or("no home directory")?)
        .map_err(|error| format!("harness state: {}", error.kind()))?;
    let state: Value = serde_json::from_str(&text).map_err(|_| "harness state is not JSON")?;
    match (state["port"].as_u64(), state["token"].as_str()) {
        (Some(port), Some(token)) => {
            Ok(json!({ "base_url": format!("http://127.0.0.1:{port}"), "token": token }))
        }
        _ => Err("harness state has no port or token".into()),
    }
}

/// Send the shell's own request to the harness and return its answer. It carries no Origin
/// header, which is how the harness tells the shell from the renderer.
fn post(route: &str, body: Value) -> Result<Value, String> {
    let harness = harness()?;
    let url = format!(
        "{}{route}",
        harness["base_url"].as_str().unwrap_or_default()
    );
    let token = format!("Bearer {}", harness["token"].as_str().unwrap_or_default());
    let mut response = ureq::post(&url)
        .config()
        .http_status_as_error(false)
        .build()
        .header("Authorization", token)
        .send_json(body)
        .map_err(|_| "the harness did not answer")?;
    let answer: Value = response
        .body_mut()
        .read_json()
        .map_err(|_| "the harness answer is not JSON")?;
    if response.status().is_success() {
        Ok(answer)
    } else {
        Err(answer["message"].as_str().unwrap_or("refused").into())
    }
}

/// Send the owner's Pause or Cancel to the harness as a command on whichever job is live. It is
/// the same path the window's buttons and the phrase take; the answer is the job's actual state,
/// and the command is in the ledger for the window to show, so the shell keeps nothing.
fn control(action: &str) -> Result<Value, String> {
    static SENT: AtomicU64 = AtomicU64::new(0);
    let id = format!("shell-{}-{}", std::process::id(), SENT.fetch_add(1, Ordering::SeqCst));
    post("/v1/control", json!({ "command_id": id, "action": action }))
}

/// Tell the harness which folder the owner picked; the answer names it by handle and label only.
fn register(purpose: &str, folder: &Path) -> Result<Value, String> {
    post("/v1/grants", json!({ "purpose": purpose, "path": folder }))
}

/// Open the native folder picker and grant what the owner picks. The path goes from the picker
/// to the harness; the renderer supplies only the purpose and receives no path. Cancelling
/// answers null.
#[tauri::command]
async fn grant_folder(window: tauri::Window, purpose: String) -> Result<Value, String> {
    let title = match purpose.as_str() {
        "output_root" => "Choose an output folder",
        _ => "Choose a source folder",
    };
    let (send, receive) = mpsc::channel();
    let parent = window.clone();
    window
        .run_on_main_thread(move || {
            let dialog = rfd::AsyncFileDialog::new()
                .set_title(title)
                .set_parent(&parent);
            let _ = send.send(dialog.pick_folder());
        })
        .map_err(|error| error.to_string())?;
    let picked = receive.recv().map_err(|error| error.to_string())?;
    match picked.await {
        Some(folder) => register(&purpose, folder.path()),
        None => Ok(Value::Null),
    }
}

fn main() {
    // Always spawn: the harness exits at once when another instance holds the profile lock, so
    // spawning and then reading its state file is start-or-reconnect.
    let sidecar = env::current_exe()
        .expect("the shell has a path")
        .with_file_name("dsp-harness");
    let mut command = Command::new(sidecar);
    if tauri::is_dev() {
        command.arg("--dev");
    }
    // The shell owns the harness only while the process it spawned is still running; one that
    // exited at once found another instance already serving this profile.
    let owned = Arc::new(AtomicBool::new(false));
    if let Ok(mut child) = command.spawn() {
        owned.store(true, Ordering::SeqCst);
        let owned = owned.clone();
        thread::spawn(move || {
            let _ = child.wait();
            owned.store(false, Ordering::SeqCst);
        });
    }

    tauri::Builder::default()
        .menu(|app| {
            let pause = MenuItem::with_id(app, "pause", "Pause", true, Some("CmdOrCtrl+P"))?;
            let cancel =
                MenuItem::with_id(app, "cancel", "Cancel run", true, Some("CmdOrCtrl+."))?;
            let quit =
                MenuItem::with_id(app, "quit", "Quit DS Playground", true, Some("CmdOrCtrl+Q"))?;
            let menu = Submenu::with_items(app, "DS Playground", true, &[&pause, &cancel, &quit])?;
            Menu::with_items(app, &[&menu])
        })
        .on_menu_event(move |app, event| {
            if event.id() == "pause" || event.id() == "cancel" {
                // The owner's Pause or Cancel: one command to the harness, answered by the ledger.
                let _ = control(event.id().as_ref());
            }
            if event.id() == "quit" {
                // Explicit Quit: the harness this shell started finishes work in progress, then
                // stops. A harness started elsewhere is left running.
                if owned.load(Ordering::SeqCst) {
                    let _ = post("/v1/shutdown", json!({}));
                }
                app.exit(0);
            }
        })
        .invoke_handler(tauri::generate_handler![harness, grant_folder])
        .run(tauri::generate_context!())
        .expect("the shell runs");
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::time::Duration;

    /// R26, C23, A24, A44: the shell's own requests turn a picked folder into a grant in a real
    /// harness, with no path in the answer the renderer receives; send Pause and Cancel as
    /// commands with IDs of their own; and stop that harness on Quit.
    #[test]
    fn a_picked_folder_becomes_a_grant_in_a_real_harness() {
        let home = env::temp_dir().join(format!("dsp-shell-test-{}", std::process::id()));
        let folder = home.join("picked folder");
        fs::create_dir_all(&folder).unwrap();
        env::set_var("DSP_HOME", &home);
        let mut server = Command::new("../../.venv/bin/python")
            .args(["-m", "dsp.harness"])
            .spawn()
            .unwrap();
        let started = (0..150).any(|_| {
            thread::sleep(Duration::from_millis(100));
            harness().is_ok() && register("source_root", &folder).is_ok()
        });
        let granted = register("source_root", &folder);
        let missing = register("output_root", &home.join("absent"));
        let unknown = register("everything", &folder);
        let paused = control("pause");
        let cancelled = control("cancel");
        let stopping = post("/v1/shutdown", json!({}));
        let exited = (0..100).any(|_| {
            thread::sleep(Duration::from_millis(100));
            server.try_wait().unwrap().is_some()
        });
        let _ = server.kill();
        let stopped = register("source_root", &folder);
        fs::remove_dir_all(&home).unwrap();

        assert!(started, "the harness did not start");
        let granted = granted.unwrap();
        assert_eq!(granted["purpose"], "source_root");
        assert_eq!(granted["label"], "picked folder");
        assert_eq!(granted["state"], "active");
        assert!(!granted.to_string().contains(home.to_str().unwrap()));
        assert_eq!(missing, Err("no such folder".into()));
        assert_eq!(
            unknown,
            Err("a grant needs an absolute path and a known purpose".into())
        );
        let paused = paused.unwrap();
        assert_eq!(paused["operation"], "pause");
        assert_eq!(paused["state"], "rejected");
        assert_eq!(paused["because"], "no job is live");
        let cancelled = cancelled.unwrap();
        assert_eq!(cancelled["operation"], "cancel");
        assert_eq!(cancelled["state"], "rejected");
        assert_ne!(paused["command"], cancelled["command"]);
        assert_eq!(stopping, Ok(json!({ "status": "stopping" })));
        assert!(exited, "the harness did not stop when the shell asked");
        assert_eq!(stopped, Err("the harness did not answer".into()));
    }
}
