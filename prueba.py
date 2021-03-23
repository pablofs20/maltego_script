from maltego_trx.transform import MaltegoTransform
import sys


if __name__ == "__main__":
	email = sys.argv[2]
	m = MaltegoTransform()
	m.addEntity("um.Faculty", email)
	m.addEntity("maltego.Person", "Capullos")
	print(m.returnOutput())
