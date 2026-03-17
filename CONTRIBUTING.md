# Contributing

Thanks for contributing to RepoSage.

## Development notes

- Keep changes focused and easy to review.
- Prefer small pull requests over large rewrites.
- Do not commit `.env` files or secrets.
- Update [README.md](/C:/Users/User/Desktop/repoproject/README.md) when setup or workflow changes.
- Add or update tests when behavior changes.

## Local workflow

1. Copy `.env.example` to `.env`.
2. Run `docker compose up --build`.
3. Run `pytest` for backend checks.
4. Run `npm run build --workspace @reposage/web` for frontend verification.

