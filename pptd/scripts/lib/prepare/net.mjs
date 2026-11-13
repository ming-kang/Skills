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
    const response = await fetch(current, {
      headers,
      redirect: 'manual',
      signal: AbortSignal.timeout(timeoutMs),
    });
    if (response.status >= 300 && response.status < 400) {
      const location = response.headers?.get?.('location');
      if (!location) throw new Error(`${label} redirect missing location: ${current}`);
      const next = new URL(location, current);
      validateUrl(next);
      current = next.href;
      continue;
    }
    if (!response.ok) throw new Error(`${label} fetch failed (${response.status}): ${current}`);
    const lengthHeader = Number(response.headers?.get?.('content-length') ?? 0);
    if (lengthHeader > maxBytes) {
      throw new Error(`${label} exceeds the ${Math.round(maxBytes / (1024 * 1024))} MiB download limit`);
    }
    const data = Buffer.from(await response.arrayBuffer());
    if (data.length > maxBytes) {
      throw new Error(`${label} exceeds the ${Math.round(maxBytes / (1024 * 1024))} MiB download limit`);
    }
    return data;
  }
  throw new Error(`too many redirects fetching ${label}: ${url}`);
}
