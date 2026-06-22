import { ElMessage } from 'element-plus'

export function useToast() {
  function showToast(message: string, type: 'success' | 'error' | 'info' | 'warning' = 'info', duration = 3000) {
    ElMessage({
      message,
      type,
      duration,
      showClose: true,
    })
  }

  return { showToast }
}
