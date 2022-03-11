import subprocess
import multiprocessing
from multiprocessing import Lock, Queue, Pool
import logging
import sys
import os

POOL_SIZE = 3
#-----------------------------------------------------------------------------
__author__     = 'Upinder Sujlana'
__copyright__  = 'Copyright 2021'
__version__    = '1.0.0'
__maintainer__ = 'Upinder Sujlana'
__status__     = 'demo'
#-----------------------------------------------------------------------------
logfilename=os.path.join(os.path.dirname(os.path.realpath(__file__)), 'processing.log')
logging.basicConfig(
    level=logging.ERROR,
    format='[%(asctime)s] {%(pathname)s:%(lineno)d} %(levelname)s - %(message)s',
    datefmt='%d-%m-%Y:%H:%M:%S',
    handlers=[
        logging.FileHandler(logfilename, mode='a'),
        logging.StreamHandler()
    ]
)
#----------------------------------------------------------------------------------
def run_local_cmd(work_queue, lock, buffer_queue):
    try:
        #Ensure the below code is only run by one process as a time. 
        while not work_queue.empty():

            #To ensure only one process takes out one element out of the work_queue
            with lock:
                cmd = work_queue.get_nowait()#Get one command out of the work_queue at a time            
            #lock.acquire()

            logging.debug("process ID of process that is working: "+ str(multiprocessing.current_process()) )
            run_cmd = subprocess.Popen(cmd,shell=True, stdout=subprocess.PIPE, encoding='utf8')            
            cmd_output, error = run_cmd.communicate()
            run_cmd_status = run_cmd.wait()
            buffer = cmd_output.split('\n')

            #Create a dictionary of the command and the output & put in the buffer_queue
            with lock:
                buffer_queue.put({cmd : buffer})

            #Release the lock so the next process can start doing its thing with the code block
            #lock.release()
    except:
        logging.error("Error running commands locally, stacktrace : ", exc_info=True)
        sys.exit(1)
#----------------------------------------------------------------------------------
def main():
    logging.debug("Top level, Parent Python PID : " + str(os.getpid()) )    
    work_queue = Queue()
    lock = Lock()

    #Create a Queue for exchanging/buffering the output
    buffer_queue = Queue()

    #Create a Queue for work that needs to be done
    commands = [
    "ifconfig | grep -E 'inet addr|inet|HW' | grep -v '127.0.0.1'",
    "id",
    "uname -a",
    "df -h",
    "free -t -m",
    "lsblk"]   
    for command in commands:
        work_queue.put(command)

    #Create a pool of processes and make them process the commands in work_queue and place their outputs
    #as a dictionary into the buffer_queue also use the lock to ensure no race condition       
    pool_of_processes = Pool(POOL_SIZE, run_local_cmd,(work_queue, lock, buffer_queue),)    
    pool_of_processes.close()
    pool_of_processes.join()
    

    #Now the commands have been processed. Lets present the data out.
    results_dictionary={}
    while not buffer_queue.empty():
        results_dictionary.update(buffer_queue.get())
    for k in results_dictionary:
        print ("Command run : " + str(k))
        print ("Output is : \n")
        for x in results_dictionary[k]:
            print (x)
        print ("==============================================================")

    #Below is a code block to flag if process pools are still hanging around
    if multiprocessing.active_children():
        logging.error("Strange still have pool processes hanging around.")
#----------------------------------------------------------------------------------------------------------
if __name__ ==  '__main__':
    main()