import sqlite3

conexion = sqlite3.connect("playlist.db")
consulta = conexion.cursor()

sql      = """ 
CREATE TABLE IF NOT EXISTS playlist(
id INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
nombre_cancion VARCHAR(100) NOT NULL,
nombre_artista VARCHAR(100) NOT NULL,
nombre_album VARCHAR(100) NOT NULL,
uri VARCHAR(100) NOT NULL
)"""

if(consulta.execute(sql)):
	print("TABLA CREADA CON EXITO")
else:
	print("HA OCURRIDO UN ERROR AL CREAR LA TABLA")

consulta.close()
conexion.commit()
conexion.close()