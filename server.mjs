import {createServer} from 'node:http';
import {readFile} from 'node:fs/promises';
import {resolve,extname,sep} from 'node:path';
const root=resolve(process.env.SERVE_DIST==='1'?'dist':'.');
const mime={'.html':'text/html','.js':'text/javascript','.css':'text/css','.json':'application/json'};
createServer(async(req,res)=>{
  if(req.method!=='GET'){res.writeHead(404);res.end('No backend is configured.');return;}
  try {const pathname=decodeURIComponent(new URL(req.url,'http://localhost').pathname);const file=resolve(root,'.'+(pathname==='/'?'/index.html':pathname));if(!file.startsWith(root+sep)||!(file.endsWith('/index.html')||file.startsWith(root+sep+'src'+sep)))throw Error();const data=await readFile(file);res.writeHead(200,{'Content-Type':mime[extname(file)]||'text/plain','Cache-Control':'no-store'});res.end(data);}catch{res.writeHead(404);res.end('Not found');}
}).listen(Number(process.env.PORT)||5173,'127.0.0.1',()=>console.log('Frontend: http://127.0.0.1:'+(process.env.PORT||5173)));
