#include <stdlib.h>
#include <hdf5.h>
#include <math.h>
#include <sys/time.h>



double clock_s(){
  struct timeval tp;
  gettimeofday(&tp,NULL);
  return tp.tv_sec+tp.tv_usec*1.0e-6;
}

void writeGroups(const char * fileName, int n){
  double t_i = clock_s();  
  printf("Entering writeGroups at %f\n",t_i);
  hid_t fapl = H5Pcreate(H5P_FILE_ACCESS);
  H5Pset_libver_bounds(fapl,H5F_LIBVER_LATEST,H5F_LIBVER_LATEST);
  hid_t f = H5Fcreate(fileName,H5F_ACC_TRUNC, H5P_DEFAULT,fapl);
  hsize_t dims[] = {1024,1024};
  int data_size = dims[0]*dims[1];
  int * data = malloc(sizeof(int)*data_size);
  for(int i = 0;i<data_size;i++){
    data[i] = rand();
  }
  for(int i = 0;i<n;i++){
    char buffer[1024];
    sprintf(buffer,"entry_%d",i);
    hid_t entry = H5Gcreate(f,buffer,0,H5P_DEFAULT,H5P_DEFAULT);
    hid_t data_1 = H5Gcreate(entry,"data_1",0,H5P_DEFAULT,H5P_DEFAULT);
    hid_t ds = H5Screate_simple(2, dims,NULL);
    hid_t dataset = H5Dcreate(data_1,"data",H5T_NATIVE_INT,ds,H5P_DEFAULT,H5P_DEFAULT,H5P_DEFAULT);
    herr_t err = H5Dwrite(dataset, H5T_NATIVE_INT, H5S_ALL, H5S_ALL, H5P_DEFAULT, data);
    if(err < 0){
      abort();
    }
    H5Dclose(dataset);
    H5Sclose(ds);
    H5Gclose(data_1);
    H5Gclose(entry);        
  }
  H5Fclose(f);
  H5close();
  free(data);
  double t_e = clock_s();
  printf("Exiting writeGroups at %f\n",t_e);
  float dt = t_e-t_i;
  printf("Write %d groups time used = %fs\n",n,dt);
  printf("Writing time per group = %fms\n",1000.0*dt/n);
}

void readGroups(const char * fileName, int n, int to_read){
  double t_i = clock_s();
  printf("Entering readGroups at %f\n",t_i);
  hsize_t dims[] = {1024,1024};
  int data_size = dims[0]*dims[1];
  int * data = malloc(sizeof(int)*data_size);
  hid_t fapl = H5Pcreate(H5P_FILE_ACCESS);
  H5Pset_libver_bounds(fapl,H5F_LIBVER_LATEST,H5F_LIBVER_LATEST);
  hid_t f = H5Fopen(fileName, H5F_ACC_RDONLY,fapl);
  for(int i = 0;i<to_read;i++){
    int j = rand()%n;
    char buffer[1024];
    sprintf(buffer,"/entry_%d/data_1/data",j);
    hid_t dataset = H5Dopen(f,buffer,H5P_DEFAULT);
    herr_t err = H5Dread(dataset,H5T_NATIVE_INT,H5S_ALL,H5S_ALL,H5P_DEFAULT,data);
    if(err < 0){
      abort();
    }
    H5Dclose(dataset);
  }
  H5Fclose(f);
  H5close();
  free(data);
  double t_e = clock_s();
  printf("Exiting readGroups at %f\n",t_e);
  float dt = t_e-t_i;
  printf("Read %d groups time used = %fs\n",to_read,dt);
  printf("Reading time per group = %fms\n",1000.0*dt/to_read);
}


int main(){
  for(int i = 5;i<18;i++){
    char buffer[1024];
    sprintf(buffer,"groupsBench-%d.cxi",i);
    writeGroups(buffer,pow(2,i));
    readGroups(buffer,pow(2,i),1000);
  }
}
