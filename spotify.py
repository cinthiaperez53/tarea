import argparse 
import BaseHTTPServer
import codecs
import json
import re
import sys
import time
import urllib
import urllib2
import webbrowser
import sqlite3

class SpotifyAPI:
	
	# Requires an OAuth token.
	def __init__(self, auth):
		self._auth = auth
	
	# Obtiene un recurso de la API de Spotify y devuelve el objeto.
	def get(self, url, params={}, tries=3):
		# Construct the correct URL.
		if not url.startswith('https://api.spotify.com/v1/'):
			url = 'https://api.spotify.com/v1/' + url
		if params:
			url += ('&' if '?' in url else '?') + urllib.urlencode(params)
	
		# Try the sending off the request a specified number of times before giving up.
		for _ in xrange(tries):
			try:
				req = urllib2.Request(url)
				req.add_header('Authorization', 'Bearer ' + self._auth)
				return json.load(urllib2.urlopen(req))
			except urllib2.HTTPError as err:
				log('Couldn\'t load URL: {} ({} {})'.format(url, err.code, err.reason))
				time.sleep(2)
				log('Trying again...')
		sys.exit(1)
	
	# The Spotify API breaks long lists into multiple pages. This method automatically
	# fetches all pages and joins them, returning in a single list of objects.
	def list(self, url, params={}):
		response = self.get(url, params)
		items = response['items']
		while response['next']:
			response = self.get(response['next'])
			items += response['items']
		return items
	
	@staticmethod
	def authorize(client_id, scope):
		webbrowser.open('https://accounts.spotify.com/authorize?' + urllib.urlencode({
			'response_type': 'token',
			'client_id': client_id,
			'scope': scope,
			'redirect_uri': 'http://127.0.0.1:{}/redirect'.format(SpotifyAPI._SERVER_PORT)
		}))
	
	
		server = SpotifyAPI._AuthorizationServer('127.0.0.1', SpotifyAPI._SERVER_PORT)
		try:
			while True:
				server.handle_request()
		except SpotifyAPI._Authorization as auth:
			return SpotifyAPI(auth.access_token)
	
	# The port that the local server listens on. Don't change this,
	# as Spotify only will redirect to certain predefined URLs.
	_SERVER_PORT = 43019
	
	class _AuthorizationServer(BaseHTTPServer.HTTPServer):
		def __init__(self, host, port):
			BaseHTTPServer.HTTPServer.__init__(self, (host, port), SpotifyAPI._AuthorizationHandler)
		
		# Disable the default error handling.
		def handle_error(self, request, client_address):
			raise
	
	class _AuthorizationHandler(BaseHTTPServer.BaseHTTPRequestHandler):
		def do_GET(self):
			# The Spotify API has redirected here, but access_token is hidden in the URL fragment.
			# Read it using JavaScript and send it to /token as an actual query string...
			if self.path.startswith('/redirect'):
				self.send_response(200)
				self.send_header('Content-Type', 'text/html')
				self.end_headers()
				self.wfile.write('<script>location.replace("token?" + location.hash.slice(1));</script>')
			
			# Read access_token 
			elif self.path.startswith('/token?'):
				self.send_response(200)
				self.send_header('Content-Type', 'text/html')
				self.end_headers()
				self.wfile.write('<script>close()</script>Thanks! You may now close this window.')
				raise SpotifyAPI._Authorization(re.search('access_token=([^&]*)', self.path).group(1))
			
			else:
				self.send_error(404)
		
		# Disable the default logging.
		def log_message(self, format, *args):
			pass
	
	class _Authorization(Exception):
		def __init__(self, access_token):
			self.access_token = access_token

def log(str):
	print u'[{}] {}'.format(time.strftime('%I:%M:%S'), str).encode(sys.stdout.encoding, errors='replace')

def main():
	# Parse arguments.
	parser = argparse.ArgumentParser(description='Exports your Spotify playlists. By default, opens a browser window '
	                                           + 'to authorize the Spotify Web API, but you can also manually specify'
	                                           + ' an OAuth token with the --token option.')
	parser.add_argument('--token', metavar='OAUTH_TOKEN', help='use a Spotify OAuth token (requires the '
	                                           + '`playlist-read-private` permission)')
	parser.add_argument('--format', default='txt', choices=['json', 'txt'], help='output format (default: txt)')
	parser.add_argument('file', help='output filename', nargs='?')
	args = parser.parse_args()
	
	# If they didn't give a filename, then just prompt them. (They probably just double-clicked.)
	if not args.file:
		args.file = raw_input('Ingrese nombre del archivo (ej. playlists.txt): ')
	
	# Se inicia sesion
	if args.token:
		spotify = SpotifyAPI(args.token)
	else:
		spotify = SpotifyAPI.authorize(client_id='f5974fcabea04d0d982603480e090557', scope='playlist-read-private')
	
	# Get the ID of the logged in user.
	me = spotify.get('me')
	log(u'Logged in as {display_name} ({id})'.format(**me))

	# List all playlists and all track in each playlist.
	playlists = spotify.list('users/{user_id}/playlists'.format(user_id=me['id']), {'limit': 50})
	for playlist in playlists:
		log(u'Loading playlist: {name} ({tracks[total]} songs)'.format(**playlist))
		playlist['tracks'] = spotify.list(playlist['tracks']['href'], {'limit': 100})


	nombre_db = "BD/playlist.db"
	conexion  = sqlite3.connect(nombre_db)
	conexion.text_factory = str
	cursor    = conexion.cursor()
	
	# Write the file.
	with codecs.open(args.file, 'w', 'utf-8') as f:
		# JSON file.
		if args.format == 'json':
			json.dump(playlists, f)
		
		# Tab-separated file.
		elif args.format == 'txt':
			for playlist in playlists:
				#f.write(playlist['name'] + '\r\n')
				for track in playlist['tracks']:
					f.write(u'{name};{artists};{album};{uri}\r\n'.format(
						uri=track['track']['uri'],
						name=track['track']['name'],
						artists=', '.join([artist['name'] for artist in track['track']['artists']]),
						album=track['track']['album']['name']
					))

					
				f.write('\r\n')
	log('Wrote file: ' + args.file)

	archivo = open(args.file,'r')
	i = 1
	for row in archivo:
		if i< 30:
			info = row.split(";")
			cursor.execute("INSERT INTO playlist(id,nombre_cancion,nombre_artista,nombre_album,uri) VALUES (?,?,?,?,?)",(i,info[0],info[1],info[2],info[3]))
		i=i+1
	archivo.close()
	conexion.commit()
	conexion.close()	
if __name__ == '__main__':
	main()