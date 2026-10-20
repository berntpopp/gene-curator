// Helpers to reach into a script-setup component's state from tests.
export type Vm = Record<string, unknown>

export const vmOf = (wrapper: { vm: unknown }): Vm => wrapper.vm as Vm

/** Call a function exposed by the component's setup scope. */
export const call = (vm: Vm, name: string, ...args: unknown[]): Promise<void> & void =>
  (vm[name] as (...a: unknown[]) => Promise<void> & void)(...args)
