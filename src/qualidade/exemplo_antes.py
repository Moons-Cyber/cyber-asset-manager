def calc(v,f):
 r=0
 for x in v:
  r+=x["severidade"]*f
 return r

def find(a,id):
 for x in a:
  if x["id"]==id:return x
 return None

def main():
 ativos=[{"id":1,"nome":"Notebook A","vulnerabilidades":[{"severidade":8.5},{"severidade":7.0}]},{"id":2,"nome":"Servidor B","vulnerabilidades":[{"severidade":9.0}]}]
 print(calc(ativos[0]["vulnerabilidades"],1.2))
 print(find(ativos,2))

if __name__=="__main__":main()