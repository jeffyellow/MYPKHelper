chrome.action.onClicked.addListener(async (tab) => {
  // Only inject on localhost (the MYPKHelper frontend)
  if (!tab.url.includes('localhost')) {
    return
  }

  try {
    await chrome.scripting.executeScript({
      target: { tabId: tab.id },
      func: startRegionSelection,
    })
  } catch (err) {
    console.error('Failed to inject selection script:', err)
  }
})

function startRegionSelection() {
  // Notify the frontend app to start region selection mode
  window.postMessage({ type: 'MYPK_START_REGION_SELECT' }, '*')
}
