fn main() {
    // Listing the commands makes them deny-by-default: only a capability can allow one.
    let manifest = tauri_build::AppManifest::new().commands(&["harness", "grant_folder"]);
    tauri_build::try_build(tauri_build::Attributes::new().app_manifest(manifest))
        .expect("tauri-build runs");
}
