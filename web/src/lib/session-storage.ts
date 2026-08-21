const ACTIVE_WORKSPACE_KEY = "docna-active-workspace"

export function persistActiveWorkspaceId(workspaceId: string | null): void {
  try {
    if (workspaceId) sessionStorage.setItem(ACTIVE_WORKSPACE_KEY, workspaceId)
    else sessionStorage.removeItem(ACTIVE_WORKSPACE_KEY)
  } catch {
    // sessionStorage may be unavailable in restricted contexts
  }
}

export function readActiveWorkspaceId(): string | null {
  try {
    return sessionStorage.getItem(ACTIVE_WORKSPACE_KEY)
  } catch {
    return null
  }
}
