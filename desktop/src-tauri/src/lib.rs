use std::io::{Read, Write};
use std::net::TcpStream;
use std::path::{Path, PathBuf};
use std::process::{Child, Command, Stdio};
use std::sync::Mutex;
use std::time::Duration;

use tauri::Manager;

const DEFAULT_PORT: u16 = 8765;
const PORT_SCAN_END: u16 = 8799;
const HEALTH_PATH: &str = "/api/health";

struct BackendState {
    child: Mutex<Option<Child>>,
    owned: Mutex<bool>,
    port: Mutex<u16>,
}

fn dev_project_root() -> PathBuf {
    PathBuf::from(env!("CARGO_MANIFEST_DIR"))
        .join("../..")
        .canonicalize()
        .unwrap_or_else(|_| PathBuf::from(env!("CARGO_MANIFEST_DIR")).join("../.."))
}

fn resolve_project_root(app: &tauri::AppHandle) -> Result<PathBuf, String> {
    if let Ok(raw) = std::env::var("VIDEO_TRANS_ROOT") {
        let path = PathBuf::from(raw.trim());
        if path.join("start.py").is_file() {
            return Ok(path);
        }
    }

    if let Ok(dir) = app.path().resource_dir() {
        let marker = dir.join("project_root.txt");
        if marker.is_file() {
            if let Ok(raw) = std::fs::read_to_string(&marker) {
                let path = PathBuf::from(raw.trim());
                if path.join("start.py").is_file() {
                    return Ok(path);
                }
            }
        }
    }

    let dev = dev_project_root();
    if dev.join("start.py").is_file() {
        return Ok(dev);
    }

    Err(
        "找不到 Video Trans 项目目录（缺少 start.py）。\n\
         请先运行 ./scripts/install_local.sh，或通过 scripts/launch_client.sh 启动。"
            .into(),
    )
}

fn preflight(root: &Path) -> Result<(), String> {
    if !root.join("start.py").is_file() {
        return Err(format!("缺少 start.py：{}", root.display()));
    }
    if !root.join("venv").is_dir() {
        return Err(
            "未找到 venv 目录。\n请在项目根目录运行：./scripts/install_local.sh".into(),
        );
    }
    let python = python_executable(root);
    if !python.exists() && python.to_string_lossy() == "python3" {
        return Err(
            "未找到 Python 虚拟环境。\n请在项目根目录运行：./scripts/install_local.sh".into(),
        );
    }
    Ok(())
}

fn python_executable(root: &Path) -> PathBuf {
    let venv_python = root.join("venv/bin/python");
    if venv_python.exists() {
        return venv_python;
    }
    PathBuf::from("python3")
}

fn augmented_path() -> String {
    let current = std::env::var("PATH").unwrap_or_default();
    format!("/opt/homebrew/bin:/usr/local/bin:{current}")
}

fn backend_url(port: u16) -> String {
    format!("http://127.0.0.1:{port}/")
}

fn spawn_backend(root: &Path, port: u16) -> Result<Child, String> {
    let python = python_executable(root);
    let start = root.join("start.py");

    Command::new(python)
        .arg(start)
        .arg("--desktop")
        .arg("--prod")
        .current_dir(root)
        .env("PATH", augmented_path())
        .env("VIDEO_TRANS_ROOT", root)
        .env("PORT", port.to_string())
        .env("HOST", "127.0.0.1")
        .stdout(Stdio::null())
        .stderr(Stdio::null())
        .spawn()
        .map_err(|e| format!("无法启动后端进程（端口 {port}）：{e}"))
}

fn http_request(port: u16, path: &str) -> Option<String> {
    let mut stream = TcpStream::connect(("127.0.0.1", port)).ok()?;
    stream
        .set_read_timeout(Some(Duration::from_secs(4)))
        .ok()?;
    stream
        .set_write_timeout(Some(Duration::from_secs(4)))
        .ok()?;
    let req = format!(
        "GET {path} HTTP/1.1\r\nHost: 127.0.0.1\r\nConnection: close\r\n\r\n"
    );
    stream.write_all(req.as_bytes()).ok()?;
    let mut buf = Vec::with_capacity(4096);
    stream.read_to_end(&mut buf).ok()?;
    String::from_utf8(buf).ok()
}

fn backend_http_ready(port: u16) -> bool {
    let Some(body) = http_request(port, HEALTH_PATH) else {
        return false;
    };
    body.contains("HTTP/1.1 200") && body.contains("video-trans")
}

fn wait_for_backend(port: u16, timeout_secs: u64) -> bool {
    let attempts = timeout_secs.saturating_mul(2);
    for _ in 0..attempts {
        if backend_http_ready(port) {
            return true;
        }
        std::thread::sleep(Duration::from_millis(500));
    }
    false
}

fn port_open(port: u16) -> bool {
    TcpStream::connect(("127.0.0.1", port)).is_ok()
}

fn find_existing_backend_port() -> Option<u16> {
    for port in DEFAULT_PORT..=PORT_SCAN_END {
        if backend_http_ready(port) {
            return Some(port);
        }
    }
    None
}

fn show_error_dialog(message: &str) {
    let escaped = message.replace('\\', "\\\\").replace('"', "\\\"");
    let script = format!(
        "display alert \"Video Trans 启动提示\" message \"{escaped}\" as warning"
    );
    let _ = Command::new("osascript").arg("-e").arg(script).status();
}

fn stop_backend(state: &BackendState) {
    let owned = state.owned.lock().map(|g| *g).unwrap_or(false);
    if !owned {
        return;
    }
    if let Ok(mut guard) = state.child.lock() {
        if let Some(mut child) = guard.take() {
            let _ = child.kill();
            let _ = child.wait();
        }
    }
}

fn ensure_backend(root: &Path) -> Result<(Option<Child>, bool, u16), String> {
    if let Some(port) = find_existing_backend_port() {
        return Ok((None, false, port));
    }

    for port in DEFAULT_PORT..=PORT_SCAN_END {
        if port_open(port) {
            // 端口被占但 health 未通过：可能是正在启动中的后端，短暂等待
            if wait_for_backend(port, 8) {
                return Ok((None, false, port));
            }
            continue;
        }

        let mut child = match spawn_backend(root, port) {
            Ok(c) => c,
            Err(_) => continue,
        };

        if wait_for_backend(port, 120) {
            return Ok((Some(child), true, port));
        }

        let _ = child.kill();
        let _ = child.wait();
    }

    Err(
        "无法在 8765–8799 端口范围内启动后端。\n\
         请关闭占用这些端口的程序后重试，或手动运行 ./scripts/run_local.sh。"
            .into(),
    )
}

fn startup_with_fallback(app: &tauri::AppHandle) {
    let window = match app.get_webview_window("main") {
        Some(w) => w,
        None => return,
    };
    let _ = window.hide();

    let startup = (|| -> Result<(Option<Child>, bool, u16), String> {
        let root = resolve_project_root(app)?;
        preflight(&root)?;
        ensure_backend(&root)
    })();

    match startup {
        Ok((child, owned, port)) => {
            app.manage(BackendState {
                child: Mutex::new(child),
                owned: Mutex::new(owned),
                port: Mutex::new(port),
            });
            let url = backend_url(port);
            if let Err(e) = window.navigate(url.parse().expect("backend url")) {
                show_error_dialog(&format!("无法打开界面：{e}"));
            }
            let _ = window.show();
        }
        Err(e) => {
            show_error_dialog(&e);
            // 仍展示 loading 页，避免 Tauri setup 返回 Err 导致 macOS 崩溃
            let _ = window.show();
        }
    }
}

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    tauri::Builder::default()
        .plugin(tauri_plugin_opener::init())
        .setup(|app| {
            startup_with_fallback(app.handle());
            Ok(())
        })
        .on_window_event(|window, event| {
            if let tauri::WindowEvent::CloseRequested { .. } = event {
                if let Some(state) = window.app_handle().try_state::<BackendState>() {
                    stop_backend(&state);
                }
            }
        })
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}
