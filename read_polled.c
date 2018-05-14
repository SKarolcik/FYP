// gcc -Wall -pthread -o chip_poll read_polled.c

#include <stdio.h>
#include <stdlib.h>
#include <poll.h>
#include <fcntl.h>

int main()
{
	FILE *kernel_file, *out_file;
	short revent;
	struct pollfd pfds[2];
	int i, fp;
	char string_in[10];

	//ptr_file = fopen("/dev/adccomms", "r");
	out_file = fopen("out_readings.dat", "w");	
	
	if (!out_file)
	{
	  printf ("Can't open file!\n"); 
	  return 1;
	}
	
	fp = open("/dev/adccomms", O_RDONLY);
	kernel_file = fdopen(fp,"r");
	pfds[0].fd = fp;
	pfds[0].events = POLLIN;
	pfds[1].fd = -1;

	//int c1,c2,c3;
	
	while(1)
	{
	  i = poll(pfds,2,-1);
  	  if (i == -1) 
	  {
	    perror("poll");
	    exit(EXIT_FAILURE);
	  }
	  revent = pfds[0].revents;
	  if (revent & POLLIN) {
	    fgets(string_in, 10, kernel_file);
            fputs(string_in, out_file);
	  }
		
	   
	}

	fclose(out_file);
	return 0;
}