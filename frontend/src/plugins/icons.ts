import { defineComponent, h } from 'vue'
import { VSvgIcon } from 'vuetify/components/VIcon'
import { aliases } from 'vuetify/iconsets/mdi-svg'
import type { IconOptions } from 'vuetify'
import { mdiPaths } from './iconPaths'
import { logService } from '@/services/logService'

const warned = new Set<string>()

// Unmapped mdi-* names (e.g. admin-written schema icons) get a placeholder instead of a blank icon.
function pathFor(name: string, raw?: string): string | undefined {
  if (mdiPaths[name]) return mdiPaths[name]
  if (!name.startsWith('mdi-')) return raw
  if (!warned.has(name)) {
    warned.add(name)
    logService.warn('Unknown icon, using fallback', { icon: name })
  }
  return mdiPaths['mdi-help-circle-outline']
}

// `icon` may carry extra classes ('mdi-loading mdi-spin'); unknown strings pass through (Vuetify's own $aliases are SVG paths).
const MdiPathIcon = defineComponent({
  props: {
    icon: { type: String, default: undefined },
    // required by Vuetify's IconComponent contract (vue-tsc rejects an optional tag)
    // eslint-disable-next-line vue/require-default-prop
    tag: { type: String, required: true as const }
  },
  setup: props => () => {
    const [name = '', ...rest] = (props.icon ?? '').split(/\s+/)
    return h(VSvgIcon, { tag: props.tag, icon: pathFor(name, props.icon), class: rest })
  }
})

export const icons: IconOptions = {
  defaultSet: 'mdi',
  aliases,
  sets: { mdi: { component: MdiPathIcon } }
}
