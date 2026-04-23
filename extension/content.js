let isSelecting = false
let startX = 0
let startY = 0
let overlay = null
let selectionBox = null

window.addEventListener('message', (event) => {
  if (event.data?.type === 'MYPK_START_REGION_SELECT') {
    startSelection()
  }
})

function startSelection() {
  if (isSelecting) return
  isSelecting = true

  // Create fullscreen overlay
  overlay = document.createElement('div')
  overlay.style.cssText = `
    position: fixed;
    top: 0;
    left: 0;
    width: 100vw;
    height: 100vh;
    background: rgba(0, 0, 0, 0.3);
    z-index: 999999;
    cursor: crosshair;
  `

  selectionBox = document.createElement('div')
  selectionBox.style.cssText = `
    position: fixed;
    border: 2px dashed #1b61c9;
    background: rgba(27, 97, 201, 0.1);
    pointer-events: none;
    display: none;
  `

  overlay.appendChild(selectionBox)
  document.body.appendChild(overlay)

  overlay.addEventListener('mousedown', onMouseDown)
  overlay.addEventListener('mousemove', onMouseMove)
  overlay.addEventListener('mouseup', onMouseUp)
}

function onMouseDown(e) {
  startX = e.clientX
  startY = e.clientY
  selectionBox.style.display = 'block'
  selectionBox.style.left = startX + 'px'
  selectionBox.style.top = startY + 'px'
  selectionBox.style.width = '0px'
  selectionBox.style.height = '0px'
}

function onMouseMove(e) {
  if (!isSelecting) return
  const currentX = e.clientX
  const currentY = e.clientY

  const left = Math.min(startX, currentX)
  const top = Math.min(startY, currentY)
  const width = Math.abs(currentX - startX)
  const height = Math.abs(currentY - startY)

  selectionBox.style.left = left + 'px'
  selectionBox.style.top = top + 'px'
  selectionBox.style.width = width + 'px'
  selectionBox.style.height = height + 'px'
}

function onMouseUp(e) {
  if (!isSelecting) return

  const endX = e.clientX
  const endY = e.clientY

  const left = Math.min(startX, endX)
  const top = Math.min(startY, endY)
  const width = Math.abs(endX - startX)
  const height = Math.abs(endY - startY)

  cleanup()

  // Send region data to the frontend app
  window.postMessage(
    {
      type: 'MYPK_REGION_SELECTED',
      region: { x: left, y: top, width, height },
    },
    '*'
  )
}

function cleanup() {
  isSelecting = false
  if (overlay) {
    overlay.remove()
    overlay = null
  }
  selectionBox = null
}
