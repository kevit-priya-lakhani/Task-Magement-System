interface ToastProps {
  message: string;
  type: 'success' | 'error';
  onDismiss: () => void;
}

export default function Toast({ message, type, onDismiss }: ToastProps) {
  return (
    <div className={`toast toast-${type}`} role="alert" aria-live="assertive">
      <span className="toast-icon" aria-hidden="true">
        {type === 'success' ? '✓' : '!'}
      </span>
      <span className="toast-msg">{message}</span>
      <button className="toast-close" onClick={onDismiss} aria-label="Dismiss notification">
        ×
      </button>
    </div>
  );
}
