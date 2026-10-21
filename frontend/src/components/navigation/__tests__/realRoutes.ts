import { createMemoryHistory, createRouter, type RouteRecordRaw, type Router } from 'vue-router'
import appRouter from '@/router'

const stub = { render: () => null }

/** The app's real route table (names, paths, meta) with stub components, on memory history. */
export function makeRealRouter(): Router {
  const routes = appRouter
    .getRoutes()
    .map(r =>
      r.redirect
        ? ({ path: r.path, name: r.name, meta: r.meta, redirect: r.redirect } as RouteRecordRaw)
        : ({ path: r.path, name: r.name, meta: r.meta, component: stub } as RouteRecordRaw)
    )
  return createRouter({ history: createMemoryHistory(), routes })
}
