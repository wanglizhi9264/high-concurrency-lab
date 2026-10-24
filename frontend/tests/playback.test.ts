import { describe, it, expect, vi, afterEach } from 'vitest'
import { mount } from '@vue/test-utils'
import { computed, defineComponent } from 'vue'
import { usePlayback } from '../src/composables/usePlayback'
afterEach(() => vi.useRealTimers())
describe('replay controls', () => {
  it('steps,pauses,resets and cleans up timers', () => {
    vi.useFakeTimers()
    const component = defineComponent({
      setup() {
        return usePlayback(computed(() => 3))
      },
      template: '<div>{{index}}</div>',
    })
    const wrapper = mount(component)
    wrapper.vm.next()
    expect(wrapper.vm.index).toBe(1)
    wrapper.vm.play()
    vi.advanceTimersByTime(650)
    expect(wrapper.vm.index).toBe(2)
    expect(wrapper.vm.playing).toBe(false)
    wrapper.vm.reset()
    expect(wrapper.vm.index).toBe(0)
    wrapper.vm.play()
    wrapper.unmount()
    expect(vi.getTimerCount()).toBe(0)
  })
})
