import { useEffect } from "react";
import { Button } from "./ui";
import { Modal } from "./Modal";
import { useConfirm } from "@/store/confirm";

// Renders the single active confirm dialog (mounted once at the app root, next
// to <Toaster />). Replaces browser `window.confirm` with an in-app modal.
export function ConfirmHost() {
  const current = useConfirm((s) => s.current);
  const respond = useConfirm((s) => s.respond);

  // Enter confirms; Escape is handled by Modal's onClose (→ cancel).
  useEffect(() => {
    if (!current) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Enter") respond(true);
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [current, respond]);

  if (!current) return null;
  const danger = current.tone === "danger";

  return (
    <Modal
      open
      onClose={() => respond(false)}
      kicker={danger ? "Confirm action" : "Confirm"}
      title={current.title}
      footer={
        <>
          <Button variant="ghost" onClick={() => respond(false)}>
            {current.cancelLabel ?? "Cancel"}
          </Button>
          <Button variant={danger ? "destructive" : "primary"} onClick={() => respond(true)} autoFocus>
            {current.confirmLabel ?? "Confirm"}
          </Button>
        </>
      }
    >
      {current.message ? (
        <p className="text-sm text-text-muted">{current.message}</p>
      ) : (
        <p className="text-sm text-text-muted">This action cannot be undone.</p>
      )}
    </Modal>
  );
}
