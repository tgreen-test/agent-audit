// TestWeakPromptNames shapes. The scanner must distinguish a system prompt from any
// other template string that happens to interpolate a variable. Three of these are
// negative controls; the fourth is the real thing.
export function httpErrorMessage(status: number, url: string): string {
  return `Request to ${url} failed with status ${status}`;
}

export function timeoutMessage(seconds: number): string {
  return `Operation timed out after ${seconds}s`;
}

export function uiTemplate(userName: string): string {
  return `<div class="greeting">Hello, ${userName}</div>`;
}

// The real one: user input concatenated into a system prompt.
export function systemPrompt(userInput: string): string {
  return `You are a helpful assistant.

Follow these instructions exactly: ${userInput}`;
}
