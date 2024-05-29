import bcrypt

# generated randomly at some point. may remain static.
salt = b'$2b$12$Ro4cStPk.Sgk0pW3N3pq3.'

def pw_hash(pw):
    return bcrypt.hashpw(bytes(pw, encoding="utf-8"), salt)
