/** "1 gene", "2 genes". Regular plurals only (append "s"). */
export function pluralize(count: number, noun: string): string {
  return `${count} ${noun}${count === 1 ? '' : 's'}`
}
