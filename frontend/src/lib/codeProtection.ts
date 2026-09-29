export interface CodeProtectionOptions {
  onDevToolsDetected: () => void;
  onDevToolsClosed: () => void;
}

export function activateCodeProtection(options: CodeProtectionOptions): () => void {
  const { onDevToolsDetected, onDevToolsClosed } = options;

  console.warn(
    "%c CẢNH BÁO CHÍNH SÁCH SỬ DỤNG\n" +
    "%c Đây là môi trường thử nghiệm. Việc truy cập DevTools có thể vi phạm chính sách của chúng tôi.",
    "color: red; font-size: 20px; font-weight: bold;",
    "color: inherit; font-size: 14px;"
  );

  // Disable right click
  const preventContextMenu = (e: MouseEvent) => e.preventDefault();
  document.addEventListener("contextmenu", preventContextMenu);

  // Disable shortcuts
  const preventShortcuts = (e: KeyboardEvent) => {
    // F12
    if (e.key === "F12") {
      e.preventDefault();
    }
    // Ctrl+Shift+I, Ctrl+Shift+J, Ctrl+Shift+C, Ctrl+U, Ctrl+S
    if (e.ctrlKey && (
      (e.shiftKey && (e.key === "I" || e.key === "J" || e.key === "C" || e.key === "i" || e.key === "j" || e.key === "c")) ||
      e.key === "U" || e.key === "u" || e.key === "S" || e.key === "s"
    )) {
      e.preventDefault();
    }
  };
  document.addEventListener("keydown", preventShortcuts);

  // Basic DevTools detection based on window size difference (outer vs inner)
  // Note: this is a basic heuristic.
  let intervalId: any;
  
  const checkDevTools = () => {
    const threshold = 160;
    const widthDiff = window.outerWidth - window.innerWidth > threshold;
    const heightDiff = window.outerHeight - window.innerHeight > threshold;
    
    if (widthDiff || heightDiff) {
      onDevToolsDetected();
    } else {
      onDevToolsClosed();
    }
  };

  intervalId = setInterval(checkDevTools, 1000);
  checkDevTools();

  // Cleanup function
  return () => {
    document.removeEventListener("contextmenu", preventContextMenu);
    document.removeEventListener("keydown", preventShortcuts);
    clearInterval(intervalId);
    onDevToolsClosed();
  };
}
