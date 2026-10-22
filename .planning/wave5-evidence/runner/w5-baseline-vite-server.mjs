import { createServer } from '/home/bernt-popp/development/gene-curator/frontend/node_modules/vite/dist/node/index.js'
const server = await createServer({
  root: '/home/bernt-popp/development/gc-wt/monkey/frontend',
  server: {
    host: '127.0.0.1', port: 5190, strictPort: true,
    fs: { allow: [
      '/home/bernt-popp/development/gc-wt/monkey/frontend',
      '/home/bernt-popp/development/gene-curator/frontend/node_modules'
    ] }
  }
})
await server.listen()
server.printUrls()
