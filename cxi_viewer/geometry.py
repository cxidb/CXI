
class Geometry:
    def __init__(self):
        pass
    def read_detector_geometry(self,det):
        geom = numpy.eye(3,4)
        try:
            o = det["geometry_1/orientation"]
            for i in range(0,2):
                for j in range(0,3):
                    geom[i,j] = o[i*3+j]
            geom[2,0:3] = numpy.cross(geom[0,0:3],geom[1,0:3])
            print geom
        except KeyError:
            pass
        try:
            c = det["corner_position"]
            for i in range(0,3):
                geom[i,3] = c[i]
        except KeyError:
            pass
        try:
            t = det["geometry_1/translation"]
            for i in range(0,3):
                geom[i,3] = t[i]
        except KeyError:
            pass
        return geom

    def find_detectors(self,fid):
        det_id = 1;
        detectors = []
        while(True):
            try:
                path = "/entry_1/instrument_1/detector_%d" % (det_id);
                det = fid[path]
                if(len(det["data"].shape) == 2):
                    detectors.append(det)
            except KeyError:
                break
            det_id += 1
        return detectors
    def find_corners(self):
        corners = {'x':[0,0],'y':[0,0]};
        for d,g in zip(self.detectors,self.geometries):
            h = d["data"].shape[1]*d["y_pixel_size"][()]
            w = d["data"].shape[0]*d["x_pixel_size"][()]
            for x in range(-1,2,2):
                for y in range(-1,2,2):
                    v = numpy.matrix([[w*x/2.0],[h*y/2.0],[0],[1]])
                    c = g*v
                    if(corners['x'][0] > c[0]):
                        corners['x'][0] = c[0]
                    if(corners['x'][1] < c[0]):
                        corners['x'][1] = c[0]
                    if(corners['y'][0] > c[1]):
                        corners['y'][0] = c[1]
                    if(corners['y'][1] < c[1]):
                        corners['y'][1] = c[1]
                    print "corner ",c
        print corners
    def assemble_detectors(self,fid):
        print fid
        self.detectors = self.find_detectors(fid)
        self.geometries = []
        for d in self.detectors:
            geom = self.read_detector_geometry(d)
            self.geometries.append(geom)
        self.find_corners()