import { afterEach, describe, expect, it, vi } from "vitest";

import {
  getOpenPullRequests,
  getPublicRepository,
  getPullRequest,
} from "@/lib/repositories";

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("getPublicRepository", () => {
  it("returns the canonical name of a public repository", async () => {
    const fetchMock = vi
      .fn<typeof fetch>()
      .mockResolvedValue(
        Response.json({ full_name: "sximn/code-review-agent", private: false }),
      );
    vi.stubGlobal("fetch", fetchMock);

    await expect(
      getPublicRepository("sximn/code-review-agent"),
    ).resolves.toEqual({
      fullName: "sximn/code-review-agent",
    });
    expect(fetchMock).toHaveBeenCalledWith(
      "https://api.github.com/repos/sximn/code-review-agent",
      expect.objectContaining({ cache: "no-store" }),
    );
  });

  it.each([
    [404, {}],
    [200, { full_name: "owner/private", private: true }],
    [200, { private: false }],
  ])(
    "returns null for status %s with an unavailable repository",
    async (status, body) => {
      vi.stubGlobal(
        "fetch",
        vi
          .fn<typeof fetch>()
          .mockResolvedValue(Response.json(body, { status })),
      );

      await expect(getPublicRepository("owner/repository")).resolves.toBeNull();
    },
  );

  it("throws when GitHub returns an error", async () => {
    vi.stubGlobal(
      "fetch",
      vi
        .fn<typeof fetch>()
        .mockResolvedValue(Response.json({}, { status: 503 })),
    );

    await expect(getPublicRepository("owner/repository")).rejects.toThrow(
      "GitHub returned 503",
    );
  });
});

describe("getOpenPullRequests", () => {
  it("parses pull requests and detects a next page", async () => {
    const fetchMock = vi.fn<typeof fetch>().mockResolvedValue(
      Response.json(
        [
          {
            number: 42,
            head: { sha: "a".repeat(40) },
            html_url: "https://github.com/owner/repository/pull/42",
            title: "Improve review handling",
            body: null,
            updated_at: "2026-09-18T10:30:00.000Z",
          },
        ],
        {
          headers: {
            link: '<https://api.github.com/resource?page=2>; rel="next"',
          },
        },
      ),
    );
    vi.stubGlobal("fetch", fetchMock);

    const result = await getOpenPullRequests("owner/repository", {
      page: 1,
      perPage: 25,
    });

    expect(result).toEqual({
      pullRequests: [
        {
          number: 42,
          headSha: "a".repeat(40),
          url: "https://github.com/owner/repository/pull/42",
          title: "Improve review handling",
          description: "",
          updatedAt: new Date("2026-09-18T10:30:00.000Z"),
        },
      ],
      hasNextPage: true,
    });
    expect(String(fetchMock.mock.calls[0]?.[0])).toContain(
      "state=open&sort=updated&direction=desc&page=1&per_page=25",
    );
  });

  it.each([
    { page: 0, perPage: 25 },
    { page: 1.5, perPage: 25 },
    { page: 1, perPage: 0 },
    { page: 1, perPage: 101 },
  ])("rejects invalid pagination: $page/$perPage", async (pagination) => {
    await expect(
      getOpenPullRequests("owner/repository", pagination),
    ).rejects.toThrow("Invalid pull request pagination parameters");
  });

  it("rejects malformed GitHub data", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn<typeof fetch>().mockResolvedValue(
        Response.json([
          {
            number: "42",
            html_url: "not-a-url",
            title: "Invalid",
            body: null,
            updated_at: "yesterday",
          },
        ]),
      ),
    );

    await expect(
      getOpenPullRequests("owner/repository", { page: 1, perPage: 25 }),
    ).rejects.toThrow();
  });
});

describe("getPullRequest", () => {
  it("resolves the current head from a fresh server request", async () => {
    const fetchMock = vi.fn<typeof fetch>().mockResolvedValue(
      Response.json({
        number: 42,
        html_url: "https://github.com/owner/repository/pull/42",
        title: "Updated PR",
        body: null,
        updated_at: "2026-10-13T10:00:00Z",
        head: { sha: "b".repeat(40) },
      }),
    );
    vi.stubGlobal("fetch", fetchMock);
    expect((await getPullRequest("owner/repository", 42))?.headSha).toBe(
      "b".repeat(40),
    );
    expect(fetchMock).toHaveBeenCalledWith(
      "https://api.github.com/repos/owner/repository/pulls/42",
      expect.objectContaining({ cache: "no-store" }),
    );
  });
  it("returns null for a missing PR", async () => {
    vi.stubGlobal(
      "fetch",
      vi
        .fn<typeof fetch>()
        .mockResolvedValue(Response.json({}, { status: 404 })),
    );
    expect(await getPullRequest("owner/repository", 42)).toBeNull();
  });
  it("rejects a missing SHA instead of scheduling an unversioned review", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn<typeof fetch>().mockResolvedValue(
        Response.json({
          number: 42,
          html_url: "https://github.com/owner/repository/pull/42",
          title: "Invalid",
          body: null,
          updated_at: "2026-10-13T10:00:00Z",
        }),
      ),
    );
    await expect(getPullRequest("owner/repository", 42)).rejects.toThrow();
  });
});
