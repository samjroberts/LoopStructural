from .process_data import ProcessInputData
import numpy as np
import pandas as pd
import networkx 

from LoopStructural.utils import getLogger
logger = getLogger(__name__)
class Map2LoopProcessor(ProcessInputData):
    def __init__(self,m2l_directory,use_thickness=None):
        """Function to build a ProcessInputData object for using m2l data

        Parameters
        ----------
        m2l_directory : path
            path to a m2l root directory
        """
        groups = pd.read_csv(m2l_directory + '/tmp/all_sorts_clean.csv', index_col=0)
        orientations = pd.read_csv(m2l_directory + '/output/orientations_clean.csv')
        formation_thickness = pd.read_csv(m2l_directory+'/output/formation_summary_thicknesses.csv')
        contacts = pd.read_csv(m2l_directory + '/output/contacts_clean.csv')
        fault_displacements = pd.read_csv(m2l_directory + '/output/fault_displacements3.csv')
        fault_orientations = pd.read_csv(m2l_directory + '/output/fault_orientations.csv')
        fault_locations = pd.read_csv(m2l_directory + '/output/faults.csv')
        fault_dimensions = pd.read_csv(m2l_directory + '/output/fault_dimensions.csv',index_col='Fault')
        fault_graph = networkx.read_gml(m2l_directory + '/tmp/fault_network.gml')
        fault_orientations.rename(columns={'formation':'fault_name'},inplace=True)
        bb = np.loadtxt(m2l_directory + '/tmp/bbox.csv',skiprows=1,delimiter=',')
        fault_dimensions['displacement'] = np.nan
        fault_dimensions['downthrow_dir'] = np.nan
        fault_dimensions['dip_dir'] = np.nan
        for fname in fault_dimensions.index:
            fault_dimensions.loc[fname,'displacement'] = fault_displacements.loc[fault_displacements['fname']==fname,'vertical_displacement'].max()
            fault_dimensions.loc[fname,'downthrow_dir'] = fault_displacements.loc[fault_displacements.loc[fault_displacements['fname']==fname,'vertical_displacement'].idxmax(),'downthrow_dir']
            fault_dimensions.loc[fname,'dip_dir'] = fault_orientations.loc[fault_orientations['fault_name']==fname,'DipDirection'].median()
        fault_properties = fault_dimensions.rename(columns={'Fault':'fault_name','InfluenceDistance':'minor_axis','VerticalRadius':'intermediate_axis','HorizontalRadius':'major_axis'})
        self.process_downthrow_direction(fault_properties,fault_orientations)
        fault_orientations['strike'] = fault_orientations['DipDirection'] + 90

            
        fault_locations.rename(columns={'formation':'fault_name'},inplace=True)
        intrusions = None
        fault_stratigraphy = None
        stratigraphic_order = []

        with open(m2l_directory + '/tmp/super_groups.csv') as f:
            for line in f:
                tmp = []
                for g in line.strip(',\n').split(','):
                    
                    tmp.extend(groups.loc[groups['group']==g,'code'].to_list())
                stratigraphic_order.append(tmp)

        # stratigraphic_order = [list(groups['code'])]
        thicknesses = dict(zip(list(formation_thickness['formation']),list(formation_thickness['thickness median'])))
        fault_properties['colour'] = 'black'
        if np.sum(orientations['polarity']==0) >0 and np.sum(orientations['polarity']==-1)==0:
            print('updating polarity')
            orientations.loc[orientations['polarity']==0,'polarity']=-1
        ip = super().__init__( 
                    contacts, 
                    orientations, 
                    stratigraphic_order,
                    thicknesses=thicknesses,
                    fault_orientations=fault_orientations,
                    fault_locations=fault_locations,
                    fault_properties=fault_properties,
                    fault_edges=list(fault_graph.edges),
                    colours=dict(zip(groups['code'],groups['colour'])),
                    fault_stratigraphy=None,
                    intrusions=None,
                    use_thickness=use_thickness
                    )
        self.origin = bb[[0,1,4]]
        self.maximum = bb[[2,3,5]]

    def process_downthrow_direction(self,fault_properties,fault_orientations):
        """Helper function to update the dip direction given downthrow direction

        Fault dip direction should point to the hanging wall

        Parameters
        ----------
        fault_properties : DataFrame
            data frame with fault name as index and downthrow direction and average dip_dir as columns 
        fault_orientations : DataFrame
            orientation data for the faults
        """                
        for fname in fault_properties.index:
            if fault_properties.loc[fname,'downthrow_dir'] == 1.0:
                logger.info("Estimating downthrow direction using fault intersections")
            # fault_intersection_angles[f]
            if np.abs(fault_properties.loc[fname,'downthrow_dir'] - fault_properties.loc[fname,'dip_dir']) > 90:
                fault_orientations.loc[fault_orientations['fault_name'] == fname, 'DipDirection'] -= 180#displacements_numpy[
#         