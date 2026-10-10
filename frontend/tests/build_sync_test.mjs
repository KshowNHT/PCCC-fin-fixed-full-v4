import {build} from 'esbuild';
import path from 'node:path';
await build({entryPoints:['tests/app_sync_test.tsx'],bundle:true,platform:'node',format:'cjs',jsx:'automatic',loader:{'.css':'empty'},external:['jsdom'],define:{'import.meta.env':'{}'},outfile:'tests/.sync_test_out.cjs',logLevel:'error',plugins:[{name:'component-fixtures',setup(b){b.onResolve({filter:/^\.\/components\/(Sidebar|MainArea)$/},()=>({path:path.resolve('tests/sync_stubs.tsx')}));}}]});
