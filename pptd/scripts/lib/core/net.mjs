// Shared bounded HTTPS downloader with explicit redirect and payload-size enforcement.
const DEFAULT_MAX_BYTES = 64 * 1024 * 1024;
const DEFAULT_TIMEOUT_MS = 30000;
const MAX_REDIRECTS = 6;

export async function fetchBounded(
  url,
  {
    label = 'resource',
    headers = {},
    maxBytes = DEFAULT_MAX_BYTES,
    timeoutMs = DEFAULT_TIMEOUT_MS,
    validateUrl = (parsed) => {
      if (parsed.protocol !== 'https:' && parsed.protocol !== 'http:') {
        throw new Error(`${label} redirected to unsupported protocol: ${parsed.protocol}`);
      }
    },
  } = {},
) {
  let current = new URL(url).href;
  for (let redirects = 0; redirects < MAX_REDIRECTS; redirects++) {
    validateUrl(new URL(current));
    const response = await fetch(current, {
      headers,
      redirect: 'manual',
      signal: AbortSignal.timeout(timeoutMs),
    });
    if (response.status >= 300 && response.status < 400) {
      await response.body?.cancel();
      const location = response.headers?.get?.('location');
      if (!location) throw new Error(`${label} redirect missing location: ${current}`);
      const next = new URL(location, current);
      current = next.href;
      continue;
    }
    if (!response.ok) {
      await response.body?.cancel();
      throw new Error(`${label} fetch failed (${response.status}): ${current}`);
    }
    const limitError = () => new Error(`${label} exceeds the ${Math.round(maxBytes / (1024 * 1024))} MiB download limit`);
    if (Number(response.headers.get('content-length') ?? 0) > maxBytes) {
      await response.body?.cancel();
      throw limitError();
    }
    const chunks = [];
    let size = 0;
    // A post-arrayBuffer size check is too late: stop reading as soon as the bound is crossed.
    // ReadableStream's async iterator cancels the body when this loop throws.
    for await (const chunk of response.body ?? []) {
      size += chunk.byteLength;
      if (size > maxBytes) throw limitError();
      chunks.push(chunk);
    }
    return Buffer.concat(chunks, size);
  }
  throw new Error(`too many redirects fetching ${label}: ${url}`);
}
