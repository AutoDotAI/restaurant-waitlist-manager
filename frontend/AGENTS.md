<!-- LOVABLE:BEGIN -->
> [!IMPORTANT]
> This project is connected to [Lovable](https://lovable.dev). Avoid rewriting
> published git history — force pushing, or rebasing/amending/squashing commits
> that are already pushed — as it rewrites history on Lovable's side and the
> user will likely lose their project history.
>
> Commits you push to the connected branch sync back to Lovable and show up in
> the editor, so keep the branch in a working state.
<!-- LOVABLE:END -->

## Project rules
- Backend is mocked behind `src/lib/waitlist/mock-api.ts` (`api` object) — the only replacement seam; UI talks to it through the React Query hooks in `src/lib/waitlist/hooks.ts`.
- Mock data persists in localStorage under `waitlist-mock-db-v1`, so refreshes keep queue state without a server.
