import { computed, onUnmounted, ref, watch, type Ref } from 'vue'
export function usePlayback(length: Ref<number>) {
  const index = ref(0),
    playing = ref(false)
  let timer: ReturnType<typeof setInterval> | undefined
  const last = computed(() => Math.max(0, length.value - 1))
  function pause() {
    if (timer) clearInterval(timer)
    timer = undefined
    playing.value = false
  }
  function next() {
    index.value = Math.min(index.value + 1, last.value)
    if (index.value === last.value) pause()
  }
  function play() {
    pause()
    if (index.value === last.value) index.value = 0
    playing.value = true
    timer = setInterval(next, 650)
  }
  function reset() {
    pause()
    index.value = 0
  }
  watch(length, reset)
  onUnmounted(pause)
  return { index, playing, last, pause, next, play, reset }
}
