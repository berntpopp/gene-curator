import { defineComponent, h } from 'vue'
import { VSvgIcon } from 'vuetify/components/VIcon'
import { aliases } from 'vuetify/iconsets/mdi-svg'
import type { IconOptions } from 'vuetify'
import { mdiPaths } from './iconPaths'

// `icon` may carry extra classes ('mdi-loading mdi-spin'); unknown strings pass through (Vuetify's own $aliases are SVG paths).
const MdiPathIcon = defineComponent({
  props: {
    icon: { type: String, default: undefined },
    tag: { type: String, required: true as const }
  },
  setup: props => () => {
    const [name = '', ...rest] = (props.icon ?? '').split(/\s+/)
    return h(VSvgIcon, { tag: props.tag, icon: mdiPaths[name] ?? props.icon, class: rest })
  }
})

export const icons: IconOptions = {
  defaultSet: 'mdi',
  aliases,
  sets: { mdi: { component: MdiPathIcon } }
}
