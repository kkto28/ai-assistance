import AppKit
import WebKit

final class RoseApplication: NSObject, NSApplicationDelegate, WKNavigationDelegate {
    private var window: NSWindow!
    private var webView: WKWebView!
    private var server: Process?
    private var serverReadyTimer: Timer?
    private var serverReadyAttempts = 0

    func applicationDidFinishLaunching(_ notification: Notification) {
        startServer()
        setRoseDockIcon()

        let configuration = WKWebViewConfiguration()
        webView = WKWebView(frame: .zero, configuration: configuration)
        webView.navigationDelegate = self

        window = NSWindow(
            contentRect: NSMakeRect(0, 0, 980, 680),
            styleMask: [.titled, .closable, .miniaturizable, .resizable],
            backing: .buffered,
            defer: false
        )
        window.title = "Rose · Personal AI"
        window.minSize = NSSize(width: 760, height: 560)
        window.center()
        window.contentView = webView
        window.makeKeyAndOrderFront(nil)
        NSApp.activate(ignoringOtherApps: true)

        waitForServer()
    }

    func applicationShouldTerminateAfterLastWindowClosed(_ sender: NSApplication) -> Bool {
        true
    }

    func applicationWillTerminate(_ notification: Notification) {
        serverReadyTimer?.invalidate()
        server?.terminate()
    }

    func webView(
        _ webView: WKWebView,
        didFail navigation: WKNavigation!,
        withError error: Error
    ) {
        waitForServer()
    }

    func webView(
        _ webView: WKWebView,
        didFailProvisionalNavigation navigation: WKNavigation!,
        withError error: Error
    ) {
        waitForServer()
    }

    private func waitForServer() {
        serverReadyTimer?.invalidate()
        serverReadyAttempts = 0
        serverReadyTimer = Timer.scheduledTimer(
            withTimeInterval: 0.25,
            repeats: true
        ) { [weak self] timer in
            guard let self = self else {
                timer.invalidate()
                return
            }
            self.checkServerHealth(timer: timer)
        }
    }

    private func checkServerHealth(timer: Timer) {
        serverReadyAttempts += 1
        if serverReadyAttempts > 80 {
            timer.invalidate()
            showStartupError("Rose server did not become ready. Try running ./Rose/run_rose_app.sh again.")
            return
        }

        guard let url = URL(string: "http://127.0.0.1:8765/api/health") else {
            return
        }
        URLSession.shared.dataTask(with: url) { [weak self] data, response, _ in
            guard let self = self else { return }
            let ready = (response as? HTTPURLResponse)?.statusCode == 200
                && data != nil
            DispatchQueue.main.async {
                guard ready else { return }
                timer.invalidate()
                var components = URLComponents(
                    string: "http://127.0.0.1:8765"
                )!
                components.queryItems = [
                    URLQueryItem(
                        name: "v",
                        value: String(Int(Date().timeIntervalSince1970))
                    )
                ]
                self.webView.load(URLRequest(url: components.url!))
            }
        }.resume()
    }

    private func startServer() {
        let fileManager = FileManager.default
        let repositoryRoot = ProcessInfo.processInfo.environment["ROSE_ROOT"]
            ?? URL(fileURLWithPath: FileManager.default.currentDirectoryPath).path
        let pythonPath = repositoryRoot + "/venv/bin/python"
        let fallbackPython = "/usr/bin/python3"
        let python = fileManager.isExecutableFile(atPath: pythonPath)
            ? pythonPath
            : fallbackPython

        server = Process()
        server?.executableURL = URL(fileURLWithPath: python)
        server?.arguments = [repositoryRoot + "/Rose/server.py"]
        server?.currentDirectoryURL = URL(fileURLWithPath: repositoryRoot)
        server?.standardOutput = FileHandle.standardOutput
        server?.standardError = FileHandle.standardError

        do {
            try server?.run()
        } catch {
            showStartupError(error.localizedDescription)
        }
    }

    private func setRoseDockIcon() {
        let repositoryRoot = ProcessInfo.processInfo.environment["ROSE_ROOT"]
            ?? FileManager.default.currentDirectoryPath
        let imagePath = repositoryRoot + "/Rose/assets/Rose.png"
        guard let source = NSImage(contentsOfFile: imagePath) else {
            return
        }

        let size = NSSize(width: 512, height: 512)
        let icon = NSImage(size: size)
        icon.lockFocus()

        NSColor.clear.setFill()
        NSBezierPath(rect: NSRect(origin: .zero, size: size)).fill()

        let iconRect = NSRect(x: 8, y: 8, width: 496, height: 496)
        let roundedRect = NSBezierPath(
            roundedRect: iconRect,
            xRadius: 112,
            yRadius: 112
        )
        roundedRect.addClip()

        NSColor(calibratedRed: 0.095, green: 0.13, blue: 0.19, alpha: 1)
            .setFill()
        roundedRect.fill()

        let sourceSize = source.size
        let scale = max(iconRect.width / sourceSize.width, iconRect.height / sourceSize.height)
        let fittedSize = NSSize(
            width: sourceSize.width * scale,
            height: sourceSize.height * scale
        )
        let imageRect = NSRect(
            x: iconRect.midX - fittedSize.width / 2,
            y: iconRect.midY - fittedSize.height / 2,
            width: fittedSize.width,
            height: fittedSize.height
        )
        source.draw(
            in: imageRect,
            from: NSRect(origin: .zero, size: sourceSize),
            operation: .sourceOver,
            fraction: 1
        )

        let border = NSBezierPath(
            roundedRect: NSInsetRect(iconRect, 5, 5),
            xRadius: 107,
            yRadius: 107
        )
        border.lineWidth = 10
        NSColor.white.setStroke()
        border.stroke()
        icon.unlockFocus()
        NSApp.applicationIconImage = icon
    }

    private func showStartupError(_ message: String) {
        let alert = NSAlert()
        alert.messageText = "Rose could not start"
        alert.informativeText = message
        alert.alertStyle = .warning
        alert.runModal()
    }
}

let application = NSApplication.shared
let delegate = RoseApplication()
application.delegate = delegate
application.setActivationPolicy(.regular)
application.run()
