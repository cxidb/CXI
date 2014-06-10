#!/usr/bin/env python

import svgwrite
from svgwrite import cm, mm  
# Just for the font metrics
from PySide import QtGui
import datetime

QtGui.QApplication([])
fm = QtGui.QFontMetrics(QtGui.QFont("Century Gothic",12))



root_fill = "rgb(159, 114, 60)"
root_stroke = "rgb(233, 185, 128)"

ds_fill = "rgb(210,131,37)"
ds_stroke = "rgb(233, 185, 128)"

group_fill = "rgb(29,97,134)"
group_stroke = "rgb(112,166,195)"

symlink_fill = "rgb(233,167,89)"
symlink_stroke = "rgb(233,185,128)"

attr_fill = "rgb(64,73,78)"
attr_stroke = "rgb(104,132,150)"

line_stroke = "rgb(67,67,67)"

px = 0.282

row_pos = 0.0

def draw_root():
    return draw_box((50,50),'/',root_fill,root_stroke,'The root of the HDF5 file')

def draw_ds(pos,title, comment=None, attr=None,attr_comment=None):
    global row_pos
    pos = draw_child(pos)
    if(attr):
        pos_attr = (pos[0]+(fm.width(title)*px+5)/2.0,pos[1])
        pos_ret = draw_attr(pos_attr,attr,attr_fill,attr_stroke,attr_comment)
        row_pos_ret = row_pos
    pos = draw_box(pos,title,ds_fill,ds_stroke,comment)
    if(attr):
        pos = pos_ret
        row_pos = row_pos_ret
#        pos = draw_attr(pos,attr,attr_fill,attr_stroke,attr_comment)
    return pos

def draw_group(pos,title,comment=None):
    pos = draw_child(pos)
    return draw_box(pos,title,group_fill,group_stroke,comment)

def draw_symlink(pos,title,target):
    pos = draw_child(pos)
    txt = 'Link to '
    pos = draw_box(pos,title,symlink_fill,symlink_stroke,None)
    width = fm.width(title)*px+5
    text = (dwg.text(txt, insert=((pos[0]+width/2.0+2.5)*mm,pos[1]*mm), fill='black',font_family='Century Gothic'))    
    if(target[-2] == '_'):
        text.add(svgwrite.text.TSpan(target,font_family='Courier',fill=group_fill,font_weight='bold'))
    else:
        text.add(svgwrite.text.TSpan(target,font_family='Courier',fill=ds_fill,font_weight='bold'))
    dwg.add(text)

def draw_box(pos,title,f,s,txt):
    global row_pos
    pos = (pos[0]+0.5*px,pos[1]-6./2)
    width = fm.width(title)*px+5
    dwg.add(dwg.rect(insert=(pos[0]*mm,pos[1]*mm), size=(width*mm, 6*mm),
                     fill=f, stroke=s, stroke_width=1,rx=2,ry=2))
    pos = ((pos[0]+width/2), (pos[1]+6./2+1.078))
    dwg.add(dwg.text(title, insert=(pos[0]*mm,pos[1]*mm), fill='white',text_anchor='middle',font_family='Century Gothic'))
    draw_comment(pos,width,txt)
#    if(txt):
#        dwg.add(dwg.text(txt, insert=((pos[0]+width/2.0+2.5)*mm,pos[1]*mm), fill='black',font_family='Century Gothic'))        
    row_pos = pos[1]-1.078
    return pos

def draw_attr(pos,title,f,s,txt):
    global row_pos
    height = 6.0
    width = fm.width(title)*px+3
    pos = (pos[0]-width/2.0,row_pos+6.0/2-1.5*px)

#    dwg.add(dwg.rect(insert=(pos[0]*mm,pos[1]*mm), size=(width*mm, height*mm),
#                     fill=f, stroke=s, stroke_width=1))
    dwg.add(dwg.rect(insert=(pos[0]*mm,pos[1]*mm), size=(width*mm, height*mm),rx=2,ry=2,
                     fill=f, stroke=s,stroke_width=1))
    pos = ((pos[0]+width/2), (pos[1]+height/2+1.078))
    dwg.add(dwg.text(title, insert=(pos[0]*mm,pos[1]*mm), fill='white',text_anchor='middle',font_family='Century Gothic'))
    draw_comment(pos,width,txt)
#    if(txt):
#        dwg.add(dwg.text(txt, insert=((pos[0]+width/2.0+2.5)*mm,pos[1]*mm), fill='black',font_family='Century Gothic'))        
    row_pos = pos[1]-1.078
    return pos

def draw_comment(pos,width,txt):
    if(txt):
        dwg.add(dwg.text(txt, insert=((pos[0]+width/2.0+2.5)*mm,pos[1]*mm), fill='black',font_family='Century Gothic'))        
    

def draw_child(pos):
    global row_pos
    pos = (pos[0],pos[1] + 1.992+0.072)
#    pos_end = (pos[0]+4.226, pos[1]+ 1.348)
    pos_end = (pos[0], row_pos+8)
    dwg.add(dwg.line((pos[0]*mm,pos[1]*mm), (pos_end[0]*mm,pos_end[1]*mm), stroke=line_stroke))
    pos_end = (pos_end[0]-0.5*px, pos_end[1]-0.5*px)
    pos = pos_end
    pos_end = (pos_end[0]+1.6,pos_end[1])
    dwg.add(dwg.line((pos[0]*mm,pos[1]*mm), (pos_end[0]*mm,pos_end[1]*mm), stroke=line_stroke))
    row_pos = pos_end[1]
    return pos_end
    

#dwg = svgwrite.Drawing('test.svg', profile='tiny')
dwg = svgwrite.Drawing('modular_detector_cxi.svg', profile='tiny')
root = draw_root()
v = draw_ds(root,'cxi_version',comment='140 (int equivalent of 1.40)')
g = draw_group(root,'entry_1',comment='The first experiment of the file')
draw_ds(g,'experiment_identifier',comment='LCLS_CXI_15234')
#draw_ds(g,'start_time',comment=datetime.datetime.now().isoformat())
sample = draw_group(g,'sample_1')
draw_ds(sample,'name',comment='"Latex spheres"')
draw_symlink(g,'data_1','instrument_1/detector_1')
ins = draw_group(g,'instrument_1')
draw_ds(ins,'name',comment='"CXI"')
src = draw_group(ins,'source_1')
draw_ds(src,'energy',comment="1.282e-15 (J) (8 keV)")
det = draw_group(ins,'detector_1',comment="CSPAD Detector")
draw_ds(det,'distance',comment="0.45 (m)")
draw_ds(det,'data',comment="Image stack with size 64 x 185 x 194",attr='axes',attr_comment="module_identifier:y:x")
draw_ds(det,'module_identifier',comment="Stack of 64 strings with the names of the modules")
draw_ds(det,'corner_positions',comment="64 x 3 array of module corner positions",attr='axes',attr_comment='module_identifier:coordinate')
draw_ds(det,'basis_vectors',comment='64 x 2 x 3 array of module basis vectors',
        attr='axes',attr_comment='module_identifier:dimension:coordinate')


dwg.save()
