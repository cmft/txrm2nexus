#!/usr/bin/python

"""
(C) Copyright 2014 Marc Rosanes
The program is distributed under the terms of the 
GNU General Public License (or the Lesser GPL).

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <http://www.gnu.org/licenses/>.
"""

import numpy as np
import nxs
import sys
import struct
import os

class SpecNormalize:

    def __init__(self, inputfile, gaussianblur):
        #Note: FF is equivalent to brightfield 
    
        filename_nexus = inputfile        
        self.input_nexusfile = nxs.open(filename_nexus, 'r')

        outputfilehdf5 = inputfile.split('.')[0]+'_specnorm'+'.hdf5'
        
        self.spectnorm = nxs.NXentry(name= "SpecNormalized")
        self.spectnorm.save(outputfilehdf5, 'w5')
        
        # Spectrographic images
        self.nFrames = 0                
        self.numrows = 0
        self.numcols = 0
        self.dim_imagesSpec = (0, 0, 1)
        self.numcurrents = 0
        self.numexptimes = 0
        self.x_pixel_size = 0
        self.y_pixel_size = 0    
        self.currents = list()
        self.exptimes = list()
        self.energies = list()
        self.angles = list()
        
        # FF images
        self.nFramesFF = 0
        self.numrowsFF = 0
        self.numcolsFF = 0
        self.dim_imagesFF = (1, 1, 0)
        self.numcurrentsFF = 0
        self.numexptimesFF = 0
        self.currents_FF = list()
        self.exptimes_FF = list()
        
        self.normalizedspectrum_singleimage = 0
        
        self.bool_currents_exist = 0
        self.bool_exptimes_exist = 0
        self.bool_currentsFF_exist = 0
        self.bool_exptimesFF_exist = 0
        
        return


    def normalizeSpec(self):

        self.input_nexusfile.opengroup('NXtomo')

        #############################################    
        ## Retrieving important data from angles   ##
        #############################################
        self.input_nexusfile.opengroup('sample')
        try: 
            self.input_nexusfile.opendata('rotation_angle')
            self.angles = self.input_nexusfile.getdata()
            self.input_nexusfile.closedata()
            self.spectnorm['rotation_angle'] = self.angles
            self.spectnorm['rotation_angle'].write()  
        except:
            print("\nAngles could NOT be extracted.\n")
            try:
                self.input_nexusfile.closedata()
            except:
                pass               
        self.input_nexusfile.closegroup()

        #### Opening group instrument ###############
        self.input_nexusfile.opengroup('instrument')
    
        #############################################    
        ## Retrieving important data from energies ##
        #############################################
        self.input_nexusfile.opengroup('source')
        try: 
            self.input_nexusfile.opendata('energy')
            self.energies = self.input_nexusfile.getdata()
            self.input_nexusfile.closedata()
            self.spectnorm['energy'] = self.energies
            self.spectnorm['energy'].write()  
        except:
            print("\nEnergies could NOT be extracted.\n")
            try:
                self.input_nexusfile.closedata()
            except:
                pass
        self.input_nexusfile.closegroup()       
                
        ###########################################    
        ## Retrieving important data from sample ##
        ###########################################
        self.input_nexusfile.opengroup('sample')
        #### pixel_sizes ############################
        try: 
            self.input_nexusfile.opendata('x_pixel_size')
            self.x_pixel_size = self.input_nexusfile.getdata()
            self.input_nexusfile.closedata()
            self.input_nexusfile.opendata('y_pixel_size')
            self.y_pixel_size = self.input_nexusfile.getdata()
            self.input_nexusfile.closedata()
            self.spectnorm['x_pixel_size'] = self.x_pixel_size
            self.spectnorm['x_pixel_size'].write()
            self.spectnorm['y_pixel_size'] = self.y_pixel_size
            self.spectnorm['y_pixel_size'].write()    
        except:
            print("\nPixel size could NOT be extracted.\n")
            try:
                self.input_nexusfile.closedata()
            except:
                pass   
	    ##############################################


        self.input_nexusfile.opendata('data')
        self.infoshape = self.input_nexusfile.getinfo()
        self.dim_imagesSpec = (self.infoshape[0][0], self.infoshape[0][1], 
                               self.infoshape[0][2])
        self.nFrames = self.infoshape[0][0]
        self.numrows = self.infoshape[0][1]
        self.numcols = self.infoshape[0][2]
        print("Dimensions spectroscopy: {0}".format(self.dim_imagesSpec))
        self.input_nexusfile.closedata()
                
        # Getting the image Currents
        try: 
            self.input_nexusfile.opendata('current')
            self.currents = self.input_nexusfile.getdata()
            self.numcurrents = len(self.currents)
            self.bool_currents_exist = 1
            self.input_nexusfile.closedata()
            self.spectnorm['Currents'] = self.currents
            self.spectnorm['Currents'].write()  
        except:
            self.bool_currents_exist = 0
            try:
                self.input_nexusfile.closedata()
            except:
                pass
        
        # Getting the image Exposure Times
        try: 
            self.input_nexusfile.opendata('ExpTimes')
            self.exptimes = self.input_nexusfile.getdata()
            self.numexptimes  = len(self.exptimes)
            self.bool_exptimes_exist = 1
            self.input_nexusfile.closedata() 
            self.spectnorm['ExpTimes'] = self.exptimes
            self.spectnorm['ExpTimes'].write() 
        except:
            self.bool_exptimes_exist = 0
            try:
                self.input_nexusfile.closedata()
            except:
                pass
                
        self.input_nexusfile.closegroup()    
        
        
        ###########################################    
        ## Retrieving important data from FF     ##
        ###########################################
        self.input_nexusfile.opengroup('bright_field')
        
        self.input_nexusfile.opendata('data')
        self.infoshapeFF = self.input_nexusfile.getinfo()
        self.dim_imagesFF = (self.infoshapeFF[0][0], self.infoshapeFF[0][1], 
                             self.infoshapeFF[0][2])
        self.nFramesFF = self.infoshapeFF[0][0]
        self.numrowsFF = self.infoshapeFF[0][1]
        self.numcolsFF = self.infoshapeFF[0][2]
        print("Dimensions FF: {0}".format(self.dim_imagesFF))
        self.input_nexusfile.closedata()
        
        # Getting the FF Currents
        try: 
            self.input_nexusfile.opendata('current')
            self.currents_FF = self.input_nexusfile.getdata()
            self.numcurrentsFF = len(self.currents_FF)
            self.bool_currentsFF_exist = 1
            self.input_nexusfile.closedata()
            self.spectnorm['CurrentsFF'] = self.currents_FF
            self.spectnorm['CurrentsFF'].write()  
        except:
            self.bool_currentsFF_exist = 0
            try:
                self.input_nexusfile.closedata()
            except:
                pass
                         
        # Getting the FF Exposure Times
        try: 
            self.input_nexusfile.opendata('ExpTimes')
            self.exptimes_FF = self.input_nexusfile.getdata()
            self.numexptimesFF  = len(self.exptimes_FF)
            self.bool_exptimesFF_exist = 1
            self.input_nexusfile.closedata() 
            self.spectnorm['ExpTimesFF'] = self.exptimes_FF
            self.spectnorm['ExpTimesFF'].write() 
        except:
            self.bool_currents_exist = 0
            try:
                self.input_nexusfile.closedata()
            except:
                pass        
        
        self.input_nexusfile.closegroup() 
          
            

        ###########################################    
        ## Normalization                         ##
        ###########################################   
        if (self.bool_currents_exist == 1 and self.bool_currentsFF_exist == 1
            and self.bool_exptimes_exist == 1  
            and self.bool_exptimesFF_exist == 1 
            and self.dim_imagesFF == self.dim_imagesSpec):
            
            print("\nInformation about currents and exposure times " 
                  "(for sampleImages and FF) is present in the hdf5 file.\n")
        
            self.spectnorm['spectroscopy_normalized'] = nxs.NXfield(
                            name='spectroscopy_normalized', dtype='float32' , 
                            shape=[nxs.UNLIMITED, self.numrows, self.numcols])
            
            self.spectnorm['spectroscopy_normalized'].attrs[
                                             'Number of Frames'] = self.nFrames
            self.spectnorm['spectroscopy_normalized'].attrs[
                                                    'Pixel Rows'] = self.numrows    
            self.spectnorm['spectroscopy_normalized'].attrs[
                                                 'Pixel Columns'] = self.numcols
            self.spectnorm['spectroscopy_normalized'].write()    
                
               
            for numimg in range (0, self.nFrames):

                self.input_nexusfile.opengroup('sample')
                self.input_nexusfile.opendata('data') 
                individual_spect_image = self.input_nexusfile.getslab(
                                [numimg, 0, 0], [1, self.numrows, self.numcols])    
                self.input_nexusfile.closedata()
                self.input_nexusfile.closegroup()
                
                self.input_nexusfile.opengroup('bright_field')
                self.input_nexusfile.opendata('data') 
                individual_FF_image = self.input_nexusfile.getslab(
                            [numimg, 0, 0], [1, self.numrowsFF, self.numcolsFF])
                
                ### Formula ###
                numerator = np.array(individual_spect_image * (
                self.exptimes_FF[numimg] * self.currents_FF[numimg]))
                denominator = np.array(individual_FF_image * (
                                 self.exptimes[numimg] * self.currents[numimg]))
                self.normalizedspectrum_singleimage = np.array(numerator / (
                                               denominator), dtype = np.float32) 
                ###############
                
                slab_offset = [numimg, 0, 0]
                self.spectnorm['spectroscopy_normalized'].put(
                self.normalizedspectrum_singleimage, slab_offset, refresh=False)
                self.spectnorm['spectroscopy_normalized'].write()
                
                self.input_nexusfile.closedata()
                self.input_nexusfile.closegroup()
                
                print('Image %d has been normalized' % numimg)
                
         
            self.input_nexusfile.close()
            print('\nSpectroscopy has been normalized taking into account ' +
                   'the ExposureTimes and the MachineCurrents\n')




        elif (self.bool_currents_exist == 0 and self.bool_currentsFF_exist == 0
            and self.bool_exptimes_exist == 1  
            and self.bool_exptimesFF_exist == 1 
            and self.dim_imagesFF == self.dim_imagesSpec):
            # Exposure times exist but currents does not exist.
            print("\nInformation about Exposure Times is present but "
                   "information of currents is not .\n") 
            pass
            
        elif (self.bool_currents_exist == 1 and self.bool_currentsFF_exist == 1
            and self.bool_exptimes_exist == 0  
            and self.bool_exptimesFF_exist==0
            and self.dim_imagesFF == self.dim_imagesSpec):
            # Currents exist but Exposure times does not exist.
            print("\nInformation about Currents is present but "
                   "information of Exposure Times is not .\n")   
            pass
            
        elif (self.dim_imagesFF == self.dim_imagesSpec):
            # Nor Currents neither Experimental Times exist.
            print("\nNeither information about Currents is present nor "
                   "information of Exposure Times.\n")       
            pass

        else:
            # Normalization is not possible because dimensions of FF are not
            # equal than dimensions of images.
            print("Normalization is not possible because dimensions of FF "
                  "are not equal than dimensions of spectroscopic images")
                  
                  
          

                         
            
            
