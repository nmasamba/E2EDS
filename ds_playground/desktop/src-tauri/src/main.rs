//! The desktop shell does three things: spawn the bundled harness, hand the renderer the
//! harness address and credential, and provide a Quit menu. Everything else is in the harness.

use std::{env, fs, path::PathBuf, process::Command, thread};

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
    if let Ok(mut child) = command.spawn() {
        thread::spawn(move || child.wait());
    }

    tauri::Builder::default()
        .menu(|app| {
            let quit =
                MenuItem::with_id(app, "quit", "Quit DS Playground", true, Some("CmdOrCtrl+Q"))?;
            Menu::with_items(
                app,
                &[&Submenu::with_items(app, "DS Playground", true, &[&quit])?],
            )
        })
        .on_menu_event(|app, event| {
            if event.id() == "quit" {
                app.exit(0);
            }
        })
        .invoke_handler(tauri::generate_handler![harness])
        .run(tauri::generate_context!())
        .expect("the shell runs");
}
