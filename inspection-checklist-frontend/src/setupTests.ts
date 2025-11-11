import '@testing-library/jest-dom/vitest'

class MemoryStorage implements Storage {
  private store = new Map<string, string>()

  clear() {
    this.store.clear()
  }
  getItem(key: string) {
    return this.store.get(key) ?? null
  }
  key(index: number) {
    return Array.from(this.store.keys())[index] ?? null
  }
  removeItem(key: string) {
    this.store.delete(key)
  }
  setItem(key: string, value: string) {
    this.store.set(key, value)
  }
  get length() {
    return this.store.size
  }
}

Object.defineProperty(globalThis, 'localStorage', { value: new MemoryStorage(), configurable: true })
Object.defineProperty(globalThis, 'sessionStorage', { value: new MemoryStorage(), configurable: true })
