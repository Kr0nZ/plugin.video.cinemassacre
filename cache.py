try:
  import sqlite3 as sqlite
except:
  import sqlite as sqlite
import sys
import time

__MAXAGE__ = 24 * 60 * 60 # hrs * mins * sec
    
class cache(object):
  sql3 = False
  sql2 = False
  error = {'error':False,'msg':''}
  
  def __init__(self,dbLocation):
    
    if "sqlite3" in sys.modules:
      self.sql3 = True
      self.db = sqlite.connect(dbLocation, check_same_thread=False)
    elif "sqlite" in sys.modules:
      self.sql2 = True
      self.db = sqlite.connect(dbLocation)
    else:
      self.error['error'] = True
      self.error['msg'] = "Error, no sql found"
        
    if not self.error['error']:
      self.tableExists()
    
  def tableExists(self):
    cursor = self.db.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='cache';")
    tbl = cursor.fetchone()
    if not tbl:
      print "table does not exist"
      cursor.execute("CREATE TABLE cache(id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, data TEXT, lastupdate INTEGER)")
      self.db.commit()
    else:
      print "table exists"
      
  def get(self, name, maxAge=__MAXAGE__):
    print "GET"
    if self.error['error']:
      return False
      
    cursor = self.db.cursor()
    cursor.execute("SELECT * FROM cache WHERE name=?;",(name,))
    data = cursor.fetchone()
    print data
    if data:
      if int(time.time()) - data[3] < maxAge:
        print "returning saved data"
        return data[2]
    return False
  
  def save(self, name, data):
    if self.error['error'] or not name:
      return False
    print [data]
    cursor = self.db.cursor()
    cursor.execute("SELECT * FROM cache WHERE name=?;",(name,))
    tstdata = cursor.fetchone()
    if tstdata:
      cursor.execute("UPDATE cache SET data = ?, lastupdate = ? WHERE name = ?;", (data, int(time.time()), name))
    else:
      cursor.execute("INSERT INTO cache(name, data, lastupdate) VALUES(?,?,?);", (name, data, int(time.time())))
    self.db.commit()
    
    return True
    
  def close(self):
    self.db.close()
    
#test = cache('test.db')
#print test.get('test2')
#test.save('test2',['a','b','c'])
#print test.get('test2')

#test.db.close()
