export type PublicRepository = {
  fullName: string
}

export async function getPublicRepository(
  repository: string,
): Promise<PublicRepository | null> {
  const [owner, name] = repository.split("/")

  if (!owner || !name) {
    return null
  }

  const response = await fetch(
    `https://api.github.com/repos/${encodeURIComponent(owner)}/${encodeURIComponent(name)}`,
    {
      headers: {
        Accept: "application/vnd.github+json",
        "User-Agent": "REWY",
      },
      cache: "no-store",
    },
  )

  if (response.status === 404) {
    return null
  }

  if (!response.ok) {
    throw new Error(`GitHub returned ${response.status}`)
  }

  const data = (await response.json()) as {
    full_name?: unknown
    private?: unknown
  }

  if (typeof data.full_name !== "string" || data.private === true) {
    return null
  }

  return { fullName: data.full_name }
}
