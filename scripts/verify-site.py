#!/usr/bin/env python3
"""Controlli statici senza dipendenze. Eseguire: python3 scripts/verify-site.py."""
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlsplit, unquote
import xml.etree.ElementTree as ET
import hashlib,json,re
ROOT=Path(__file__).resolve().parents[1]
LANGS=['it','en','es','fr','de','pt']
VOID=set('area base br col embed hr img input link meta param source track wbr'.split())
class Page(HTMLParser):
 def __init__(self,path):
  super().__init__(convert_charrefs=True);self.path=path;self.stack=[];self.ids=set();self.refs=[];self.images=[];self.tags=[];self.errors=[]
 def handle_starttag(self,tag,attrs):
  a=dict(attrs);self.tags.append((tag,a))
  if len(a)!=len(attrs):self.errors.append('attributi duplicati')
  if 'id'in a:
   if a['id']in self.ids:self.errors.append('ID duplicato: '+a['id'])
   self.ids.add(a['id'])
  if tag=='img':
   self.images.append(a)
   if 'alt'not in a:self.errors.append('alt assente')
   if not {'width','height'}<=a.keys():self.errors.append('dimensioni immagine assenti')
  for attr in ['href','src']:
   if attr in a:self.refs.append(a[attr])
  if tag not in VOID:self.stack.append(tag)
 def handle_endtag(self,tag):
  if tag in VOID:self.errors.append('chiusura elemento void: '+tag);return
  if not self.stack or self.stack[-1]!=tag:self.errors.append('annidamento errato: '+tag)
  else:self.stack.pop()
 def handle_startendtag(self,tag,attrs):
  self.handle_starttag(tag,attrs)
  if tag not in VOID:self.handle_endtag(tag)
pages={}
for path in ROOT.rglob('*.html'):
 if '.git'in path.parts:continue
 p=Page(path);p.feed(path.read_text());assert not p.errors and not p.stack,(path,p.errors,p.stack);pages[path]=p
checks=0
for path,p in pages.items():
 for ref in p.refs:
  u=urlsplit(ref)
  if u.scheme or u.netloc:continue
  target=(path.parent/unquote(u.path)).resolve() if u.path else path
  if target.is_dir():target=target/'index.html'
  assert target.is_file(),(path,ref,'destinazione assente')
  if u.fragment:
   assert target in pages and unquote(u.fragment)in pages[target].ids,(path,ref,'ancora assente')
  checks+=1
weights={}
for lang in LANGS:
 path=ROOT/('index.html' if lang=='it' else lang+'/index.html');p=pages[path]
 assert next(a['lang'] for t,a in p.tags if t=='html')==lang
 assert len([1 for t,a in p.tags if t=='h1'])==1
 assert {'modalita','collezione','giornaliera','schermate','download','assistenza'}<=p.ids
 assert len([1 for t,a in p.tags if t=='article'])==6
 assert len([1 for t,a in p.tags if t=='figure' and a.get('class')=='souvenir'])==12
 assert {a['hreflang'] for t,a in p.tags if t=='link'and a.get('rel')=='alternate'}==set(LANGS+['x-default'])
 assert any(a.get('name')=='apple-itunes-app'and a.get('content')=='app-id=6774271420' for t,a in p.tags)
 assert len([1 for t,a in p.tags if t=='a'and a.get('href')=='https://apps.apple.com/app/id6774271420'])==3
 assert all(a.get('loading')=='lazy'for a in p.images if 'souvenirs/'in a['src']and a.get('alt') or a['src'].split('/')[-1]in ['home.jpg','bandiere.jpg','confronto.jpg','capitali.jpg'])
 resources={path,ROOT/'stile.css'}
 for a in p.images:
  if not urlsplit(a['src']).scheme:resources.add((path.parent/a['src']).resolve())
 # Conservative: includes all below-the-fold images, favicon and social image.
 resources|={ROOT/'assets/favicon.png',ROOT/'assets/og.jpg'}
 weight=sum(x.stat().st_size for x in resources);assert weight<1500000
 weights[lang]=weight
ET.parse(ROOT/'sitemap.xml')
assert hashlib.sha1(b'blob '+str((ROOT/'privacy/index.html').stat().st_size).encode()+b'\0'+(ROOT/'privacy/index.html').read_bytes()).hexdigest()=='28ec551ade6f9e745e2562ae628c1c29dec76f8b'
print(json.dumps({'pagine':len(pages),'link_interni_verificati':checks,'byte_locali_per_lingua':weights,'privacy':'identica alla partenza'},indent=2))
print('Struttura, sezioni, lingue, immagini, sitemap e link: OK. Questo script non è un validatore HTML5 completo.')
