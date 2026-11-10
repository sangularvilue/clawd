import numpy as np, sys
from mp import Canvas
names = sys.argv[1:]
W,H=1900,len(names)*130+20
c=Canvas(W,H)
g=np.ones((H,W,3),np.float32)*np.array([0.5,0.38,0.28])
g[:, 1000:1450]=np.array([0.15,0.2,0.4]); g[:,1450:]=np.array([0.95,0.8,0.5])
c.load(g)
for i,n in enumerate(names):
    y=45+i*130
    x=np.linspace(40,900,60)
    c.stroke(n,(0.85,0.82,0.9),np.column_stack([x,y+10*np.sin(x/60)]),r=22)
    c.stroke(n,(0.2,0.25,0.5),np.column_stack([x[5:40],y+10+10*np.sin(x[5:40]/60)]),r=12)
    x=np.linspace(940,1860,60)
    c.stroke(n,(0.75,0.1,0.08),np.column_stack([x,y+10*np.sin(x/60)]),r=10)
    c.stroke(n,(0.95,0.9,0.7),np.column_stack([x,y+50+6*np.sin(x/60)]),r=3.5)
c.save('/tmp/claude-0/-home-user-clawd/6f28c8cd-f399-5857-9655-63a48954e005/scratchpad/swatch.png')
