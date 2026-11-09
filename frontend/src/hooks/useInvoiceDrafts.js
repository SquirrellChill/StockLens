import { useSyncExternalStore } from 'react'
import { invoiceService } from '../services/invoiceService'

export function useInvoiceDrafts() {
  return useSyncExternalStore(invoiceService.subscribe, invoiceService.getDrafts)
}
