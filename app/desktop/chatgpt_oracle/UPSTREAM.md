# ChatGPT consumer-web runtime

- Upstream: https://github.com/steipete/oracle
- Package: `@steipete/oracle` 0.22.2
- License: MIT (see `LICENSE.oracle`)
- Runtime: official Node.js 24 Windows x64 distribution
- Node runtime: v24.21.0 (`node-v24.21.0-win-x64.zip`)
- Official archive SHA-256: `158f7685b44de51f6c0df1d153526cbcd3e1bc739a8dfc607721cef75de9e541`
- Extracted `node.exe` SHA-256: `ba4e6d110e8c1592a1ecd390f6b05f3da124b13871a5be62b341a07a853c6c32`
- npm integrity: `sha512-X8VuafjcnFkMw40HWtKxmdq+60iIRMdcHoZ5aqWBWEMbjaxyUGibthhBQMWHKgnalWulsIUyTWQ1J+yVeawstw==`

Oracle was selected because its Windows browser mode drives the normal
`chatgpt.com` UI, verifies GPT-6 model selection and Extra High separately,
fails closed when Extra High cannot be confirmed, and supports ChatGPT Web
Search and Deep Research. Debate AI does not use Oracle's API engine and does
not run a permanent Oracle browser host.
