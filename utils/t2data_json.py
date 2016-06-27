# Converting TOUGH2 input to JSON, for use as supermodel input.
# Use this module as a temporary drop-in replacement for t2data,
# with the json() method providing the conversion.
# It's envisaged eventually this code will be part of t2data itself.

from t2data import *
from os.path import splitext

def primary_to_region_we(primary):
    """Returns thermodynamic region deduced from primary variables for EOS we."""
    from t2thermo import region
    if primary[1] < 1.: return 4
    else: return region(primary[1], primary[0])

primary_to_region_funcs = {'we': primary_to_region_we}
    
class t2data_export_json(t2data):
    """Modification of t2data class including ability to export to
    JSON for supercode."""
    def write_exodus_json(self, geo, indent = 2, atmos_volume = 1.e25,
                           incons = None, eos = None, bdy_incons = None):
        """Exports t2data object and mulgrid geometry to ExodusII file
        and JSON file."""
        import json
        geobase, ext = splitext(geo.filename)
        exoname = geobase + '.exo'
        geo.write_exodusii(exoname)
        json_data = self.json(geo, exoname, atmos_volume, incons, eos, bdy_incons)
        datbase, ext = splitext(self.filename)
        jsonname = datbase + '.json'
        json.dump(json_data, file(jsonname, 'w'), indent = indent)

    def json(self, geo, mesh_filename, atmos_volume = 1.e25, incons = None, 
                    eos = None, bdy_incons = None):
        """Takes a t2data object and mulgrid and returns a dictionary
        representing the corresponding JSON input."""
        jsondata = {}
        jsondata['title'] = self.title.strip()
        jsondata['mesh'] = mesh_filename
        jsondata['gravity'] = self.parameter['gravity']
        jsondata['thermodynamics'] = 'ifc67'
        jsondata.update(self.eos_json(eos))
        jsondata.update(self.timestepping_json())
        jsondata.update(self.output_json())
        jsondata.update(self.rocks_json(geo, atmos_volume))
        jsondata['rock'].update(self.relative_permeability_json())
        jsondata.update(self.initial_json(geo, incons, jsondata['eos']['name']))
        jsondata.update(self.boundaries_json(geo, bdy_incons, atmos_volume,
                                             jsondata['eos']['name']))
        jsondata.update(self.generators_json(geo))
        return jsondata

    def eos_json(self, eos):
        """Converts TOUGH2 EOS data to JSON."""
        jsondata = {}
        aut2eosname = ''
        if eos is None:
            if 'eos' in self.multi:
                if self.multi['eos']: aut2eosname = self.multi['eos'].strip()
            if aut2eosname == '': aut2eosname = 'EW'
        else:
            if isinstance(eos, int):
                eos_from_index = {1: 'EW', 2: 'EWC', 3: 'EWA', 4: 'EWAV'}
                if eos in eos_from_index: aut2eosname = eos_from_index[eos]
            else: aut2eosname = eos
        eosname = {'W': 'w', 'EW': 'we'}
        if aut2eosname in eosname:
            jsondata['eos'] = {'name': eosname[aut2eosname]}
            if eosname == 'w':
                jsondata['eos']['temperature'] = self.parameter['default_incons'][1]
        else: raise Exception ('Unhandled EOS:' + aut2eosname)
        return jsondata

    def timestepping_json(self):
        """Converts TOUGH2 timestepping/ iteration parameters to JSON."""
        jsondata = {}
        tstop = self.parameter['tstop']
        if tstop == 0.0: tstop = None
        jsondata['time'] = {'start': self.parameter['tstart'],
                            'stop': tstop}
        maxit = self.parameter['max_iterations']
        if maxit is None or maxit == 0: maxit = 8
        abstol = self.parameter['absolute_error']
        if abstol == 0: abstol = 1.0
        reltol = self.parameter['relative_error']
        if reltol == 0.: reltol = 1.e-5
        jsondata['time']['step'] = \
            {'maximum': {'size': self.parameter['max_timestep'],
                         'number': self.parameter['max_timesteps']},
             'method': 'beuler',
             'solver': {'nonlinear': {'tolerance':
                                          {'absolute': abstol, 'relative': reltol},
                                      'maximum': {'iterations': maxit}}}}
        if self.parameter['const_timestep'] < 0. :
            jsondata['time']['step'].update({'sizes': self.parameter['timestep'],
                                        'adapt': {'on': False}})
        else:
            jsondata['time']['step'].update({'initial': self.parameter['const_timestep']})
            if self.parameter['option'][16] > 0:
                redlt = self.parameter['timestep_reduction']
                if redlt is None or redlt == 0:
                    redlt = 5  # default for AUTOUGH2.2
                jsondata['time']['step']['adapt'] = \
                    {'on': True, 'method': 'iteration',
                     'reduction': 1. / redlt,
                     'amplification': 2.,
                     'min': float(self.parameter['option'][16]), 'max': float(maxit)}
        return jsondata

    def rocks_json(self, geo, atmos_volume):
        """Converts TOUGH2 rocktype definition and assignment data to JSON."""
        jsondata = {}
        jsondata['rock'] = {'types': []}
        ir, rock_index = 0, {}
        for rt in self.grid.rocktypelist:
            rtdata = {'name': rt.name, 'density': rt.density, 'porosity': rt.porosity,
                      'permeability': list(rt.permeability),
                      'wet conductivity': rt.conductivity, 'specific heat': rt.specific_heat}
            dry_cond = rt.dry_conductivity
            if dry_cond is not None and dry_cond > 0.0: rtdata['dry conductivity'] = dry_cond
            rtdata['cells'] = []
            jsondata['rock']['types'].append(rtdata)
            rock_index[rt.name] = ir
            ir += 1
        for blkname in geo.block_name_list:
            blk = self.grid.block[blkname]
            rockname = blk.rocktype.name
            blk_index = geo.block_name_index[blk.name] - geo.num_atmosphere_blocks
            if 0. < blk.volume < atmos_volume:
                jsondata['rock']['types'][rock_index[rockname]]['cells'].append(blk_index)
        return jsondata

    def relative_permeability_json(self):
        """Converts TOUGH2 relative permeability data to JSON."""
        jsondata = {}
        if self.relative_permeability:
            rp = {}
            rp_types = {1: 'linear', 2: 'pickens', 3: 'corey', 4: 'grant', 5: 'fully mobile'}
            itype = self.relative_permeability['type']
            pars = self.relative_permeability['parameters']
            rp['type'] = rp_types[itype]
            if itype == 1:
                rp['liquid'] = [pars[0], pars[2]]
                rp['vapour'] = [pars[1], pars[3]]
            elif itype == 2:
                rp['power'] = pars[0]
            elif itype in [3, 4]:
                rp['slr'] = pars[0]
                rp['ssr'] = pars[1]
            jsondata['relative permeability'] = rp
        else: jsondata['relative permeability'] = {'type': 'fully mobile'}
        return jsondata
    
    def initial_json(self, geo, incons, eos):
        """Converts initial condition specifications to JSON."""
        jsondata = {}
        if incons is None:
            incs = self.parameter['default_incons'][:]
            while incs[-1] is None: incs.pop()
            jsondata['initial'] = {'primary': incs}
        elif isinstance(incons, str):
            jsondata['initial'] = {'filename': incons}
        elif isinstance(incons, t2incon):
            if eos in primary_to_region_funcs:
                jsondata['initial'] = {'primary': [], 'region': []}
                primary_to_region = primary_to_region_funcs[eos]
                for blkname in geo.block_name_list[geo.num_atmosphere_blocks:]:
                    primary = incons[blkname].variable
                    jsondata['initial']['primary'].append(primary)
                    jsondata['initial']['region'].append(primary_to_region(primary))
                if len(set(jsondata['initial']['region'])) == 1:
                    jsondata['initial']['region'] = jsondata['initial']['region'][0]
            else:
                raise Exception("Finding thermodynamic region from primary variables not yet supported for EOS:" +
                                eos)
        return jsondata

    def generators_json(self, geo):
        """Converts TOUGH2 generator data to JSON."""
        jsondata = {}
        component = {'MASS': 1, 'HEAT': 2, 'COM1': 1, 'COM2': 2}
        if self.generatorlist:
            jsondata['source'] = []
            for gen in self.generatorlist:
                if gen.type in component:
                    cell_index = geo.block_name_index[gen.block] - geo.num_atmosphere_blocks
                    g = {'cell': cell_index, 'value': gen.gx, 'component': component[gen.type]}
                    if gen.gx > 0. and gen.type <> 'HEAT': g['enthalpy'] = gen.ex
                    jsondata['source'].append(g)
                else: raise Exception('Generator type ' + gen.type + ' not supported.')
        return jsondata

    def boundaries_json(self, geo, bdy_incons, atmos_volume, eos):
        """Converts Dirichlet boundary conditions to JSON."""
        jsondata = {}
        if bdy_incons is None:
            default_incs = self.parameter['default_incons'][:]
            default_region = 1
            while default_incs[-1] is None: default_incs.pop()
            def primary(blkname): return default_incs
            def region(pv): return default_region
        else:
            def primary(blkname): return bdy_incons[blkname].variable
            if eos in primary_to_region_funcs:
                primary_to_region = primary_to_region_funcs[eos]
                def region(pv): return primary_to_region(pv)
            else:
                def region(pv): return default_region
        jsondata['boundaries'] = []
        for blk in self.grid.blocklist:
            if not (0. < blk.volume < atmos_volume):
                pv = primary(blk.name)
                bc = {'primary': pv, 'region': region(pv), 'cell normals': []}
                for conname in blk.connection_name:
                    names = list(conname)
                    names.remove(blk.name)
                    interior_blkname = names[0]
                    interior_blk = self.grid.block[interior_blkname]
                    cell_index = geo.block_name_index[interior_blkname] - geo.num_atmosphere_blocks
                    if blk.centre is None:
                        # TODO make this more general, to handle more cases
                        nz = -self.grid.connection[conname].dircos
                        if abs(nz) > 0.: normal = np.array([0., 0., nz])
                        else:
                            raise Exception("Can't find normal vector for connection: " + 
                                            str(conname))
                    else:
                        normal = blk.centre - interior_blk.centre
                    normal /= np.linalg.norm(normal)
                    bc['cell normals'].append([cell_index, list(normal)])
                jsondata['boundaries'].append(bc)
        return jsondata

    def output_json(self):
        """Converts output specifications to JSON."""
        datbase, ext = splitext(self.filename)
        jsondata = {}
        if self.parameter['print_interval'] >= self.parameter['max_timesteps']:
            print_interval = 0
        else:
            print_interval = self.parameter['print_interval']
        jsondata['output'] = {
            'filename': datbase + '.h5',
            'frequency': print_interval,
            'final': True}
        if self.parameter['option'][24] > 0: jsondata['output']['initial'] = True
        return jsondata