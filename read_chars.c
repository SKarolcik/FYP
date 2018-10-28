// gcc -Wall -pthread -o chip_read read_chars.c

#include <stdio.h>
#include <stdlib.h>

int main(int argc, char** argv)
{
	FILE *ptr_file, *out_file;
	char string_in[10];
	//printf("Number of arguments: %d\n", argc);
	//printf("Argument itself: %s\n", argv[1]);

	ptr_file = fopen("/dev/adccomms", "r");
	if (argc == 2){
	out_file = fopen(argv[1], "w");
	}else{
	out_file = fopen("out_readings.dat", "w");
	}	
	if (!ptr_file)
	{
	  printf ("Can't open input file!\n"); 
	  return 1;
	}
	if (!out_file)
	{
	  printf ("Can't open output file!\n"); 
	  return 1;
	}
	while(1)
	{
	   
	   if (fgets(string_in, 10, ptr_file) != NULL)
             fputs(string_in, out_file);
	}

	fclose(ptr_file);
	return 0;
}