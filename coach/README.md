# Coach Chris

An AI version of Chris to ask when you get stuck with DVE: installing, making a video, filming, or a strange error.

Set it up once, about two minutes:
1. At claude.ai, open Projects and create a new project called "Coach Chris".
2. Open "Set project instructions" and paste in everything from `Coach-Chris-Instructions.txt`.
3. Add `DVE-Guide.md` to the project's files.
4. Ask it anything, like "my install stopped partway" or "which style should I use for an ad?"

After a DVE update, replace `DVE-Guide.md` in the project with the new one from `~/DVE/coach/`.

It answers from the DVE guide. When the guide doesn't cover something, it says so, and for anything still stuck after two tries it sends you to the AdCamp community.
