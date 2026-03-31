import { useState, useMemo } from 'react';
import useSWR from 'swr';
import { api, Task, TaskStatus, TaskPriority } from './api/tasks';
import TaskModal from './components/TaskModal';
import Toast from './components/Toast';
import './App.css';

/* ============================================================
   Types
   ============================================================ */
interface ToastItem {
  id: number;
  message: string;
  type: 'success' | 'error';
}

/* ============================================================
   Badge components
   ============================================================ */
function PriorityBadge({ priority }: { priority: TaskPriority }) {
  const labels: Record<TaskPriority, string> = { high: 'High', medium: 'Med', low: 'Low' };
  return (
    <span className={`badge badge-priority-${priority}`} aria-label={`Priority: ${priority}`}>
      {labels[priority]}
    </span>
  );
}

function StatusBadge({ status }: { status: TaskStatus }) {
  const labels: Record<TaskStatus, string> = {
    todo: 'Todo',
    'in-progress': 'In Progress',
    done: 'Done',
  };
  const cls = status.replace('-', '');
  return (
    <span className={`badge badge-status-${cls}`} aria-label={`Status: ${status}`}>
      {labels[status]}
    </span>
  );
}

/* ============================================================
   Icons
   ============================================================ */
function CheckIcon() {
  return (
    <svg width="13" height="13" viewBox="0 0 13 13" fill="none" aria-hidden="true">
      <path d="M2 6.5L5 9.5L11 3.5" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

function EditIcon() {
  return (
    <svg width="13" height="13" viewBox="0 0 13 13" fill="none" aria-hidden="true">
      <path d="M8.5 2L11 4.5L4.5 11H2V8.5L8.5 2Z" stroke="currentColor" strokeWidth="1.5" strokeLinejoin="round" />
    </svg>
  );
}

function TrashIcon() {
  return (
    <svg width="13" height="13" viewBox="0 0 13 13" fill="none" aria-hidden="true">
      <path d="M2 3.5h9M5 3.5V2.5a.5.5 0 0 1 .5-.5h2a.5.5 0 0 1 .5.5v1M3 3.5l.5 7a.5.5 0 0 0 .5.5h5a.5.5 0 0 0 .5-.5l.5-7" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

function PlusIcon() {
  return (
    <svg width="13" height="13" viewBox="0 0 13 13" fill="none" aria-hidden="true">
      <path d="M6.5 1v11M1 6.5h11" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
    </svg>
  );
}

function SearchIcon() {
  return (
    <svg className="search-icon" width="14" height="14" viewBox="0 0 16 16" fill="none" aria-hidden="true">
      <circle cx="6.5" cy="6.5" r="5.5" stroke="currentColor" strokeWidth="1.5" />
      <path d="M11 11l3.5 3.5" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
    </svg>
  );
}

/* ============================================================
   Helpers
   ============================================================ */
function formatDate(iso: string): string {
  return new Date(iso).toLocaleDateString('en-US', {
    month: 'short',
    day: 'numeric',
    year: 'numeric',
  });
}

/* ============================================================
   TaskRow
   ============================================================ */
interface TaskRowProps {
  task: Task;
  onEdit: (task: Task) => void;
  onDelete: (id: string) => void;
  onComplete: (id: string) => void;
  deletingId: string | null;
  completingId: string | null;
}

function TaskRow({ task, onEdit, onDelete, onComplete, deletingId, completingId }: TaskRowProps) {
  const isDeleting = deletingId === task.id;
  const isCompleting = completingId === task.id;

  return (
    <tr className={task.status === 'done' ? 'row-done' : ''}>
      <td>
        <div className="cell-title">
          <span className="title-text">{task.title}</span>
          {task.description && (
            <span className="title-desc" title={task.description}>
              {task.description}
            </span>
          )}
        </div>
      </td>
      <td>
        <PriorityBadge priority={task.priority} />
      </td>
      <td>
        <StatusBadge status={task.status} />
      </td>
      <td className="cell-date">
        <span className="date-text">{formatDate(task.created_at)}</span>
      </td>
      <td>
        <div className="cell-actions">
          {task.status === 'in-progress' && (
            <button
              className="action-btn action-complete"
              onClick={() => onComplete(task.id)}
              disabled={isCompleting || isDeleting}
              title="Mark as complete"
              aria-label={`Complete task: ${task.title}`}
            >
              {isCompleting ? <span className="btn-spinner" aria-hidden="true" /> : <CheckIcon />}
            </button>
          )}
          <button
            className="action-btn action-edit"
            onClick={() => onEdit(task)}
            disabled={isDeleting}
            title="Edit task"
            aria-label={`Edit task: ${task.title}`}
          >
            <EditIcon />
          </button>
          <button
            className="action-btn action-delete"
            onClick={() => onDelete(task.id)}
            disabled={isDeleting || isCompleting}
            title="Delete task"
            aria-label={`Delete task: ${task.title}`}
          >
            {isDeleting ? <span className="btn-spinner" aria-hidden="true" /> : <TrashIcon />}
          </button>
        </div>
      </td>
    </tr>
  );
}

/* ============================================================
   App
   ============================================================ */
export default function App() {
  const [search, setSearch] = useState('');
  const [filterStatus, setFilterStatus] = useState<TaskStatus | ''>('');
  const [filterPriority, setFilterPriority] = useState<TaskPriority | ''>('');
  const [modalOpen, setModalOpen] = useState(false);
  const [editTask, setEditTask] = useState<Task | null>(null);
  const [toasts, setToasts] = useState<ToastItem[]>([]);
  const [deletingId, setDeletingId] = useState<string | null>(null);
  const [completingId, setCompletingId] = useState<string | null>(null);

  const { data: tasks, isLoading, error, mutate } = useSWR<Task[]>(
    ['tasks', filterStatus, filterPriority],
    () => api.listTasks(filterStatus || null, filterPriority || null),
    { revalidateOnFocus: false },
  );

  /* ---- Toast helpers ---- */
  const addToast = (message: string, type: 'success' | 'error') => {
    const id = Date.now();
    setToasts((prev) => [...prev, { id, message, type }]);
    setTimeout(() => removeToast(id), 4000);
  };

  const removeToast = (id: number) => {
    setToasts((prev) => prev.filter((t) => t.id !== id));
  };

  /* ---- Filtered tasks (client-side search) ---- */
  const filteredTasks = useMemo(() => {
    if (!tasks) return [];
    const q = search.trim().toLowerCase();
    if (!q) return tasks;
    return tasks.filter(
      (t) =>
        t.title.toLowerCase().includes(q) ||
        (t.description ?? '').toLowerCase().includes(q),
    );
  }, [tasks, search]);

  /* ---- Handlers ---- */
  const handleDelete = async (id: string) => {
    setDeletingId(id);
    try {
      await api.deleteTask(id);
      mutate();
      addToast('Task deleted', 'success');
    } catch (err: unknown) {
      addToast(err instanceof Error ? err.message : 'Failed to delete task', 'error');
    } finally {
      setDeletingId(null);
    }
  };

  const handleComplete = async (id: string) => {
    setCompletingId(id);
    try {
      await api.completeTask(id);
      mutate();
      addToast('Task marked complete', 'success');
    } catch (err: unknown) {
      addToast(err instanceof Error ? err.message : 'Failed to complete task', 'error');
    } finally {
      setCompletingId(null);
    }
  };

  const handleSaved = () => {
    mutate();
    addToast(editTask ? 'Task updated' : 'Task created', 'success');
    setModalOpen(false);
    setEditTask(null);
  };

  const openEdit = (task: Task) => {
    setEditTask(task);
    setModalOpen(true);
  };

  const openAdd = () => {
    setEditTask(null);
    setModalOpen(true);
  };

  const closeModal = () => {
    setModalOpen(false);
    setEditTask(null);
  };

  /* ---- Render ---- */
  return (
    <div className="app">
      {/* Header */}
      <header className="header">
        <div className="header-inner">
          <div className="header-brand">
            <div className="brand-icon" aria-hidden="true">
              <svg width="14" height="14" viewBox="0 0 14 14" fill="none">
                <rect x="1" y="1" width="5" height="5" rx="1.5" fill="white" opacity="0.9" />
                <rect x="8" y="1" width="5" height="5" rx="1.5" fill="white" opacity="0.6" />
                <rect x="1" y="8" width="5" height="5" rx="1.5" fill="white" opacity="0.6" />
                <rect x="8" y="8" width="5" height="5" rx="1.5" fill="white" opacity="0.3" />
              </svg>
            </div>
            <span className="brand-title">Task Manager</span>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
            {tasks && (
              <span className="header-meta">
                {tasks.length} task{tasks.length !== 1 ? 's' : ''}
              </span>
            )}
            <button className="btn-add" onClick={openAdd} aria-label="Add new task">
              <PlusIcon />
              Add Task
            </button>
          </div>
        </div>
      </header>

      {/* Main */}
      <main className="main">
        {/* Toolbar */}
        <div className="toolbar" role="search">
          <div className="search-wrap">
            <SearchIcon />
            <input
              className="search-input"
              type="search"
              placeholder="Search tasks…"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              aria-label="Search tasks"
            />
            {search && (
              <button
                className="search-clear"
                onClick={() => setSearch('')}
                aria-label="Clear search"
              >
                ×
              </button>
            )}
          </div>

          <div className="filters">
            <select
              className={`filter-select${filterStatus ? ' active' : ''}`}
              value={filterStatus}
              onChange={(e) => setFilterStatus(e.target.value as TaskStatus | '')}
              aria-label="Filter by status"
            >
              <option value="">All Status</option>
              <option value="todo">Todo</option>
              <option value="in-progress">In Progress</option>
              <option value="done">Done</option>
            </select>

            <select
              className={`filter-select${filterPriority ? ' active' : ''}`}
              value={filterPriority}
              onChange={(e) => setFilterPriority(e.target.value as TaskPriority | '')}
              aria-label="Filter by priority"
            >
              <option value="">All Priority</option>
              <option value="high">High</option>
              <option value="medium">Medium</option>
              <option value="low">Low</option>
            </select>
          </div>
        </div>

        {/* Table */}
        <div className="table-wrap">
          {isLoading && (
            <div className="table-state" role="status" aria-label="Loading tasks">
              <div className="spinner" />
              <span>Loading tasks…</span>
            </div>
          )}

          {error && !isLoading && (
            <div className="table-state table-error" role="alert">
              <span className="table-error-icon">⚠</span>
              <span>Failed to load tasks. Check that the server is running.</span>
            </div>
          )}

          {!isLoading && !error && (
            <>
              <table className="task-table" aria-label="Task list">
                <thead>
                  <tr>
                    <th className="col-title" scope="col">Title</th>
                    <th className="col-priority" scope="col">Priority</th>
                    <th className="col-status" scope="col">Status</th>
                    <th className="col-date" scope="col">Created</th>
                    <th className="col-actions" scope="col"><span className="sr-only">Actions</span></th>
                  </tr>
                </thead>
                <tbody>
                  {filteredTasks.length === 0 ? (
                    <tr className="empty-row">
                      <td colSpan={5}>
                        <div className="empty-state">
                          <span className="empty-icon">📋</span>
                          <span>
                            {search
                              ? `No tasks match "${search}"`
                              : 'No tasks yet — add one to get started.'}
                          </span>
                        </div>
                      </td>
                    </tr>
                  ) : (
                    filteredTasks.map((task) => (
                      <TaskRow
                        key={task.id}
                        task={task}
                        onEdit={openEdit}
                        onDelete={handleDelete}
                        onComplete={handleComplete}
                        deletingId={deletingId}
                        completingId={completingId}
                      />
                    ))
                  )}
                </tbody>
              </table>
              <div className="table-footer">
                <span className="table-count">
                  {filteredTasks.length === tasks?.length
                    ? `${filteredTasks.length} task${filteredTasks.length !== 1 ? 's' : ''}`
                    : `${filteredTasks.length} of ${tasks?.length} tasks`}
                </span>
              </div>
            </>
          )}
        </div>
      </main>

      {/* Modal */}
      {modalOpen && (
        <TaskModal
          task={editTask}
          onSaved={handleSaved}
          onError={(msg) => addToast(msg, 'error')}
          onClose={closeModal}
        />
      )}

      {/* Toasts */}
      <div className="toast-container" aria-live="polite" aria-atomic="false">
        {toasts.map((t) => (
          <Toast
            key={t.id}
            message={t.message}
            type={t.type}
            onDismiss={() => removeToast(t.id)}
          />
        ))}
      </div>
    </div>
  );
}

