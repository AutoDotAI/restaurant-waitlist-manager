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
- The UI accesses the FastAPI backend through `src/lib/waitlist/api-client.ts` and the React Query hooks in `src/lib/waitlist/hooks.ts`.
- The Makefile's `API_PORT` variable configures both the backend port and the frontend API URL; it defaults to `8001`.
- The backend owns persistent waitlist data. Staff bearer tokens are kept in sessionStorage for the current browser tab.
