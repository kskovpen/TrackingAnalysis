#!/usr/bin/env python

import os, sys, subprocess, glob
import json

from optparse import OptionParser

def main(argv = None):
    
    if argv == None:
        argv = sys.argv[1:]
        
    usage = "usage: %prog [options]\n Submit jobs"
    
    parser = OptionParser(usage)
    parser.add_option("-j", "--json", default="list.json", help="input file list [default: %default]")
    parser.add_option("-o", "--output", default="jobs", help="output directory [default: %default]")
    parser.add_option("--splitdata", type=int, default=40, help="number of files per job [default: %default]")
    parser.add_option("--splitmc", type=int, default=40, help="number of files per job [default: %default]")
#    parser.add_option("-p", "--param", default="nTracks,sumTrackPt,sumTrackPtSq", help="parameterisation for PV resolution measurement [default: %default]")
    parser.add_option("-p", "--param", default="sumTrackPtSq", help="parameterisation for PV resolution measurement [default: %default]")
    parser.add_option("--data", action='store_true', help="Only run on data [default: %default]")
    parser.add_option("--mc", action='store_true', help="Only run on mc [default: %default]")
    
    (options, args) = parser.parse_args(sys.argv[1:])
    
    return options                                        

def job(cwd,proxy,arch,js):
    
    j = "#!/bin/bash\n\n"

    j += "export X509_USER_PROXY="+proxy+"\n"

    j += "source /cvmfs/cms.cern.ch/cmsset_default.sh\n"
    j += "cd "+cwd+"/../../\n"
    j += "export SCRAM_ARCH="+arch+"\n"
    j += "eval `scramv1 runtime -sh`;cd -\n"

    out = js.replace('.json','.root')

    j += "time python "+cwd+"/./plot.py --input=" + cwd+"/"+js + " --output=" + cwd+"/"+out + " --param=" + options.param + "\n"

    sh = js.replace('.json','.sh')
    with open(sh, 'w') as f:
        f.write(j)
    
    return sh

if __name__ == '__main__':
    
    options = main()

    proxy = '/user/kskovpen/proxy/x509up_u20657'
    arch = 'slc6_amd64_gcc700'
    wt = '12:00:00'
    
    cwd = os.getcwd()
    
    os.system('cp /tmp/x509up_u20657 '+proxy)
    
    outdir = options.output
    if os.path.isdir(outdir):
        os.system("rm -rf "+outdir)
    os.system("mkdir "+outdir)

    lszdata = options.splitdata
    lszmc = options.splitmc

    with open(options.json, "r") as read_file:
        flist = json.load(read_file)
    
    for k, v in flist.items():
        
#        if (('Run20' not in k) or ('ZeroBias' not in k) or ('Run2017F' not in k)): continue
        if options.data and ('Run20' not in k): continue
#        if options.data and (('Run20' not in k) or ('ZeroBias' not in k)): continue
#        if options.mc and (('Run20' in k) or ('QCD' not in k)): continue
        if options.mc and ('Run20' in k): continue
        
        if ('ZeroBias' not in k) and ('SingleNeutrino' not in k): continue
        
#        if ('Run2017B' not in k) or ('ZeroBias' not in k): continue
        
        lsz = lszdata if ('Run20' in k) else lszmc
        
        njob = 0
        datasplit = []
        for i in range(len(v)):
            datasplit.append(v[i])
            if len(datasplit) >= lsz or i == len(v)-1:
                with open(options.output+'/list_' + k + '_' + str(njob) + '.json', 'w') as outfile:
                    data = {}; data[k] = datasplit
                    json.dump(data, outfile, indent=2)
                datasplit = []
                njob += 1

    jobs = glob.glob(options.output+'/*.json')

    for j in jobs:
        
        jname = j.replace('.json','').replace(outdir+'/list_','')
        print jname
        
        sh = cwd+'/'+job(cwd,proxy,arch,j)
        log = cwd+'/'+j.replace('.json','.log')

        NoErrors = False
        while NoErrors is False:
            try:
                res = subprocess.Popen(('qsub','-N','Plot_'+jname,'-q','localgrid','-o',log,'-j','oe',sh,'-l','walltime='+wt), stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                out, err = res.communicate()
                NoErrors = ('Invalid credential' not in err)
                if not NoErrors: print '.. Resubmitted'
            except KeyboardInterrupt:
                sys.exit(0)
            except:
                pass
