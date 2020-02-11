import numpy as np
from LoopStructural.cython.dsi_helper import cg
from LoopStructural.cython.dsi_helper import tetra_neighbours

class TetMesh:
    def __init__(self, origin = [0,0,0], nsteps = [10,10,10], step_vector = [1,1,1]):
        self.origin = np.array(origin)
        self.step_vector = np.array(step_vector)
        self.nsteps = np.array(nsteps)
        self.nsteps_cells = self.nsteps - 1
        self.n_cell_x = self.nsteps[0] - 1
        self.n_cell_y = self.nsteps[1] - 1
        self.n_cell_z = self.nsteps[2] - 1
        self.n_cells = self.n_cell_x * self.n_cell_y * self.n_cell_z
        self.n_nodes = self.nsteps[0]*self.nsteps[1]*self.nsteps[2]

        max = self.origin + self.nsteps_cells * self.step_vector
        x = np.linspace(origin[0], max[0], nsteps[0])
        y = np.linspace(origin[1], max[1], nsteps[1])
        z = np.linspace(origin[2], max[2], nsteps[2])
        xx, yy, zz = np.meshgrid(x, y, z, indexing='ij')
        self.nodes = np.array([xx.flatten(order='F'), yy.flatten(order='F'),
                               zz.flatten(order='F')]).T

        self.tetra_mask = np.array([
            [0, 6, 5, 4],
            [0, 4, 5, 3],
            [4, 6, 7, 5],
            [0, 1, 6, 4],
            [0, 6, 5, 2]])
        self.tetra_mask_even = np.array([
            [1, 2, 3, 7],
            [1, 6, 7, 2],
            [0, 1, 2, 3],
            [3, 7, 5, 2],
            [1, 7, 3, 4]])
        self.even_neighbour_mask = np.array([


        ])
        self.ntetra = self.n_cells * 5

        self.properties = {}
        self.property_gradients = {}
        self.n_elements = self.ntetra

    def barycentre(self):
        elements = self.get_elements()
        barycentre = np.sum(self.nodes[elements][:, :, :],
                                 axis=1) / 4.
        return barycentre

    def update_property(self, name, value, save=True):

        self.properties[name] = value
        # grads = self.get_elements_gradients(np.arange(self.n_elements))
        # props = self.properties[name][
        #     self.elements[np.arange(self.n_elements)]]
        # grad = np.einsum('ikj,ij->ik', grads, props)
        # self.property_gradients[name] = grad

    def evaluate_value(self, pos, prop):
        values = np.zeros(pos.shape[0])
        values[:] = np.nan
        vertices, c, tetras, inside = self.get_tetra_for_location(pos)
        #
        # bc = self.calc_bary_c(e[inside], array[inside])
        # prop_int = np.zeros(e.shape)
        # nv = np.zeros(self.properties[prop].shape)
        # nv[~self.regions[region]] = np.nan
        # nv[self.regions[region]] = self.properties[prop][self.regions[region]]
        # props = self.properties[prop][self.elements[e[inside]]]
        # prop_int[inside] = np.sum((bc.T * props), axis=1)
        # prop_int[~inside] = np.nan
        # return prop_int
        values[inside] = np.sum(c*self.properties[prop][tetras],axis=1)
        return values

    def evaluate_gradient(self, pos, prop):
        print(pos.shape)
        values = np.zeros(pos.shape)
        values[:] = np.nan
        vertices, element_gradients, tetras, inside = self.get_tetra_gradient_for_location(pos)
        print(tetras.shape, inside.shape)
        vertex_vals = self.properties[prop][tetras]
        print(vertex_vals.shape, tetras.shape, values[inside,:].shape)
        #grads = np.zeros(tetras.shape)
        values[inside,:] = (element_gradients*vertex_vals[:, None, :]).sum(2)
        length = np.sum(values[inside,:],axis=1)
        values[inside,:] /= length[:,None]
        return values

    def get_tetra_for_location(self, pos):
        pos = np.array(pos)
        # initialise array for tetrahedron vertices
        vertices = np.zeros((5, 4, pos.shape[0], 3))
        vertices[:] = np.nan
        # get cell indexes
        c_xi, c_yi, c_zi = self.position_to_cell_index(pos)

        # determine if using +ve or -ve mask
        even_mask = (c_xi + c_yi + c_zi) % 2 == 0
        # get cell corners
        xi, yi, zi = self.cell_corner_indexes(c_xi, c_yi, c_zi)  # global_index_to_node_index(gi)
        # convert to node locations
        nodes = self.node_indexes_to_position(xi, yi, zi).T

        vertices[:, :, even_mask, :] = nodes[:, even_mask, :][self.tetra_mask_even, :, :]
        vertices[:, :, ~even_mask, :] = nodes[:, ~even_mask, :][self.tetra_mask, :, :]
        # changing order to points, tetra, nodes, coord
        vertices = vertices.swapaxes(0, 2)
        vertices = vertices.swapaxes(1, 2)

        # use scalar triple product to calculate barycentric coords
        vap = pos[:, None, :] - vertices[:, :, 0, :]
        vbp = pos[:, None, :] - vertices[:, :, 1, :]
        #         # vcp = p - points[:, 2, :]
        #         # vdp = p - points[:, 3, :]
        vab = vertices[:, :, 1, :] - vertices[:, :, 0, :]
        vac = vertices[:, :, 2, :] - vertices[:, :, 0, :]
        vad = vertices[:, :, 3, :] - vertices[:, :, 0, :]
        vbc = vertices[:, :, 2, :] - vertices[:, :, 1, :]
        vbd = vertices[:, :, 3, :] - vertices[:, :, 1, :]
        va = np.einsum('ikj, ikj->ik', vbp, np.cross(vbd, vbc, axisa=2, axisb=2)) / 6.
        vb = np.einsum('ikj, ikj->ik', vap, np.cross(vac, vad, axisa=2, axisb=2)) / 6.
        vc = np.einsum('ikj, ikj->ik', vap, np.cross(vad, vab, axisa=2, axisb=2)) / 6.
        vd = np.einsum('ikj, ikj->ik', vap, np.cross(vab, vac, axisa=2, axisb=2)) / 6.
        v = np.einsum('ikj, ikj->ik', vab, np.cross(vac, vad, axisa=2, axisb=2)) / 6.

        c = np.zeros((va.shape[0], va.shape[1], 4))
        # print(va.shape)
        c[:, :, 0] = va / v
        c[:, :, 1] = vb / v
        c[:, :, 2] = vc / v
        c[:, :, 3] = vd / v

        # if all coords are +ve then point is inside cell
        mask = np.all(c > 0, axis=2)

        inside = np.any(mask,axis=1)
        # get cell corners
        xi, yi, zi = self.cell_corner_indexes(c_xi, c_yi, c_zi)

        even_mask = (c_xi + c_yi + c_zi) % 2 == 0
        gi = xi + yi * self.n_cell_x + zi * self.n_cell_x * self.n_cell_y
        tetras = np.zeros((xi.shape[0], 5, 4)).astype(int)

        tetras[even_mask, :, :] = gi[even_mask, :][:, self.tetra_mask_even]
        tetras[~even_mask, :, :] = gi[~even_mask, :][:, self.tetra_mask]

        vertices_return = np.zeros((pos.shape[0],4,3))
        vertices_return[:] = np.nan
        print(vertices[mask,:,:].shape)
        vertices_return[inside,:,:] = vertices[mask,:,:]
        c_return = np.zeros((pos.shape[0],4))
        c_return[:] = np.nan
        c_return[inside] = c[mask]
        tetra_return = np.zeros((pos.shape[0],4)).astype(int)
        tetra_return[:] = -1
        tetra_return[inside,:] = tetras[mask,:]
        return vertices_return, c_return, tetra_return, inside

    def get_constant_gradient(self, region='everywhere'):
        elements_gradients = self.get_element_gradients(np.arange(self.ntetra))
        # ps = self.nodes[self.elements[e]]
        region = region.astype('int64')

        neighbours = self.get_neighbours()
        elements = self.get_elements()
        # print('cg')
        # print(elements_gradients)
        # print(neighbours)
        # print(self.nodes)
        idc, c, ncons = cg(elements_gradients, neighbours, elements, self.nodes,
                           region)

        idc = np.array(idc[:ncons, :])
        c = np.array(c[:ncons, :])
        B = np.zeros(c.shape[0])

        return c, idc, B

    def get_elements(self):
        """

        Returns
        -------

        """
        x = np.arange(0, self.n_cell_x)
        y = np.arange(0, self.n_cell_y)
        z = np.arange(0, self.n_cell_z)

        c_xi, c_yi, c_zi = np.meshgrid(x, y, z)
        c_xi = c_xi.flatten()
        c_yi = c_yi.flatten()
        c_zi = c_zi.flatten()
        # get cell corners
        xi, yi, zi = self.cell_corner_indexes(c_xi, c_yi, c_zi)
        even_mask = (c_xi + c_yi + c_zi) % 2 == 0
        gi = xi + yi * self.nsteps[0] + zi * self.nsteps[0] * self.nsteps[1]
        tetras = np.zeros((c_xi.shape[0], 5, 4)).astype(int)
        tetras[even_mask, :, :] = gi[even_mask, :][:, self.tetra_mask_even]
        tetras[~even_mask, :, :] = gi[~even_mask, :][:, self.tetra_mask]
        return tetras.reshape((tetras.shape[0]*tetras.shape[1],tetras.shape[2]))


    def get_element_gradients(self, elements):
        """
        Get the gradients of all tetras

        Parameters
        ----------
        elements

        Returns
        -------

        """
        x = np.arange(0, self.n_cell_x)
        y = np.arange(0, self.n_cell_y)
        z = np.arange(0, self.n_cell_z)

        c_xi, c_yi, c_zi = np.meshgrid(x, y, z)
        c_xi = c_xi.flatten()
        c_yi = c_yi.flatten()
        c_zi = c_zi.flatten()
        even_mask = (c_xi + c_yi + c_zi) % 2 == 0
        # get cell corners
        xi, yi, zi = self.cell_corner_indexes(c_xi, c_yi, c_zi)  # global_index_to_node_index(gi)
        # convert to node locations
        nodes = self.node_indexes_to_position(xi, yi, zi).T

        points = np.zeros((5, 4, self.n_cells, 3))
        points[:, :, even_mask, :] = nodes[:, even_mask, :][self.tetra_mask_even, :, :]
        points[:, :, ~even_mask, :] = nodes[:, ~even_mask, :][self.tetra_mask, :, :]

        # points[:, :, even_mask, :] = nodes[:, even_mask, :][mesh.tetra_mask_even, :, :]
        # points[:, :, ~even_mask, :] = nodes[:, ~even_mask, :][mesh.tetra_mask, :, :]
        # changing order to points, tetra, nodes, coord
        points = points.swapaxes(0, 2)
        points = points.swapaxes(1, 2)
        # printpoints.shape
        # ps = points.reshape()
        ps = points.reshape(points.shape[0] * points.shape[1], points.shape[2], points.shape[3])

        m = np.array(
            [[(ps[:, 1, 0] - ps[:, 0, 0]), (ps[:, 1, 1] - ps[:, 0, 1]),
              (ps[:, 1, 2] - ps[:, 0, 2])],
             [(ps[:, 2, 0] - ps[:, 0, 0]), (ps[:, 2, 1] - ps[:, 0, 1]),
              (ps[:, 2, 2] - ps[:, 0, 2])],
             [(ps[:, 3, 0] - ps[:, 0, 0]), (ps[:, 3, 1] - ps[:, 0, 1]),
              (ps[:, 3, 2] - ps[:, 0, 2])]])
        I = np.array(
            [[-1., 1., 0., 0.],
             [-1., 0., 1., 0.],
             [-1., 0., 0., 1.]])
        m = np.swapaxes(m, 0, 2)
        element_gradients = np.linalg.inv(m)

        element_gradients = element_gradients.swapaxes(1, 2)
        element_gradients = element_gradients @ I

        return element_gradients

    def get_tetra_gradient_for_location(self, pos):
        """
        Get the gradient of the tetra for a location

        Parameters
        ----------
        pos

        Returns
        -------

        """
        vertices, bc, tetras, inside = self.get_tetra_for_location(pos)
        ps = vertices
        m = np.array(
            [[(ps[:, 1, 0] - ps[:, 0, 0]), (ps[:, 1, 1] - ps[:, 0, 1]),
              (ps[:, 1, 2] - ps[:, 0, 2])],
             [(ps[:, 2, 0] - ps[:, 0, 0]), (ps[:, 2, 1] - ps[:, 0, 1]),
              (ps[:, 2, 2] - ps[:, 0, 2])],
             [(ps[:, 3, 0] - ps[:, 0, 0]), (ps[:, 3, 1] - ps[:, 0, 1]),
              (ps[:, 3, 2] - ps[:, 0, 2])]])
        I = np.array(
            [[-1., 1., 0., 0.],
             [-1., 0., 1., 0.],
             [-1., 0., 0., 1.]])
        m = np.swapaxes(m, 0, 2)
        element_gradients = np.linalg.inv(m)

        element_gradients = element_gradients.swapaxes(1, 2)
        element_gradients = element_gradients @ I
        return vertices, element_gradients, tetras, inside

    def inside(self, pos):
        """
        Check if a point is inside the structured grid

        Parameters
        ----------
        pos

        Returns
        -------

        """
        # check whether point is inside box
        inside = np.ones(pos.shape[0]).astype(bool)
        for i in range(3):
            inside *= pos[:, i] > self.origin[None, i]
            inside *= pos[:, i] < self.origin[None, i] + \
                      self.step_vector[None, i] * self.nsteps_cells[None, i]
        return inside

    def global_node_indicies(self, indexes):
        """
        Convert from node indexes to global node index

        Parameters
        ----------
        indexes

        Returns
        -------

        """
        indexes = np.array(indexes).swapaxes(0, 2)
        return indexes[:, :, 0] + self.nsteps[None, None, 0] \
               * indexes[:, :, 1] + self.nsteps[None, None, 0] * \
               self.nsteps[None, None, 1] * indexes[:, :, 2]

    def global_cell_indicies(self, indexes):
        """
        Convert from cell indexes to global cell index

        Parameters
        ----------
        indexes

        Returns
        -------

        """
        indexes = np.array(indexes).swapaxes(0, 2)
        return indexes[:, :, 0] + self.nsteps_cells[None, None, 0] \
               * indexes[:, :, 1] + self.nsteps_cells[None, None, 0] * \
               self.nsteps_cells[None, None, 1] * indexes[:, :, 2]

    def cell_corner_indexes(self, x_cell_index, y_cell_index, z_cell_index):
        """
        Returns the indexes of the corners of a cell given its location xi,
        yi, zi

        Parameters
        ----------
        x_cell_index
        y_cell_index
        z_cell_index

        Returns
        -------

        """
        x_cell_index = np.array(x_cell_index)
        y_cell_index = np.array(y_cell_index)
        z_cell_index = np.array(z_cell_index)

        xcorner = np.array([0, 1, 0, 0, 1, 0, 1, 1])
        ycorner = np.array([0, 0, 1, 0, 0, 1, 1, 1])
        zcorner = np.array([0, 0, 0, 1, 1, 1, 0, 1])
        xcorners = x_cell_index[:, None] + xcorner[None, :]
        ycorners = y_cell_index[:, None] + ycorner[None, :]
        zcorners = z_cell_index[:, None] + zcorner[None, :]
        return xcorners, ycorners, zcorners

    def position_to_cell_corners(self, pos):
        """
        Find the nodes that belong to a cell which contains a point

        Parameters
        ----------
        pos

        Returns
        -------

        """
        inside = self.inside(pos)
        ix, iy, iz = self.position_to_cell_index(pos)
        cornersx, cornersy, cornersz = self.cell_corner_indexes(ix, iy, iz)
        globalidx = self.global_cell_indicies(
            np.dstack([cornersx, cornersy, cornersz]).T)
        return globalidx, inside

    def position_to_cell_index(self, pos):
        """
        Find which cell a point is in

        Parameters
        ----------
        pos

        Returns
        -------

        """
        ix = pos[:, 0] - self.origin[None, 0]
        iy = pos[:, 1] - self.origin[None, 1]
        iz = pos[:, 2] - self.origin[None, 2]
        ix = ix // self.step_vector[None, 0]
        iy = iy // self.step_vector[None, 1]
        iz = iz // self.step_vector[None, 2]
        return ix.astype(int), iy.astype(int), iz.astype(int)

    def node_indexes_to_position(self, xindex, yindex, zindex):
        """
        Get the xyz position from the node coordinates

        Parameters
        ----------
        xindex
        yindex
        zindex

        Returns
        -------

        """
        x = self.origin[0] + self.step_vector[0] * xindex
        y = self.origin[1] + self.step_vector[1] * yindex
        z = self.origin[2] + self.step_vector[2] * zindex

        return np.array([x, y, z])

    def global_index_to_node_index(self, global_index):
        """
        Convert from global indexes to xi,yi,zi

        Parameters
        ----------
        global_index

        Returns
        -------

        """
        # determine the ijk indices for the global index.
        # remainder when dividing by nx = i
        # remained when dividing modulus of nx by ny is j
        x_index = global_index % self.nsteps[0, None]
        y_index = global_index // self.nsteps[0, None] % \
                  self.nsteps[1, None]
        z_index = global_index // self.nsteps[0, None] // \
                  self.nsteps[1, None]
        return x_index, y_index, z_index

    def global_index_to_cell_index(self, global_index):
        """
        Convert from global indexes to xi,yi,zi

        Parameters
        ----------
        global_index

        Returns
        -------

        """
        # determine the ijk indices for the global index.
        # remainder when dividing by nx = i
        # remained when dividing modulus of nx by ny is j

        x_index = global_index % self.nsteps_cells[0, None]
        y_index = global_index // self.nsteps_cells[0, None] % \
                  self.nsteps_cells[1, None]
        z_index = global_index // self.nsteps_cells[0, None] // \
                  self.nsteps_cells[1, None]
        return x_index, y_index, z_index

    def get_neighbours(self):
        """
        This function goes through all of the elements in the mesh and assembles a numpy array
        with the neighbours for each element

        Returns
        -------

        """
        # for each cell
        # cell_neighbours = np.zeros((self.ntetra, 4)).astype(int)
        # cell_neighbours[:] = -1
        neighbours = np.zeros((self.n_elements,4)).astype(int)
        neighbours[:] = -1
        tetra_neighbours(self.get_elements(),neighbours)
        return neighbours



