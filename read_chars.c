// gcc -Wall -pthread -o chip_read read_chars.c

#include <stdio.h>
#include <stdlib.h>

int main()
{
	FILE *ptr_file, *out_file;
	char string_in[10];

	ptr_file = fopen("/dev/adccomms", "r");
	out_file = fopen("out_readings.dat", "w");	
	if (!ptr_file)
	{
	  printf ("Can't open file!\n"); 
	  return 1;
	}
	if (!out_file)
	{
	  printf ("Can't open file!\n"); 
	  return 1;
	}
	int c1,c2,c3;
	while(1)
	{
	   
	   if (fgets(string_in, 10, ptr_file) != NULL)
             fputs(string_in, out_file);
	   /*
	   c1 = fgetc(ptr_file);
	   if (c1 != 0 && c1 != -1 && c1 != 10 && c1 != EOF)
	   {
		c2 = fgetc(ptr_file);
		c3 = fgetc(ptr_file);
		c1 = (c1 - 48)*100 + (c2 - 48)*10 + (c3 - 48);
		fprintf(out_file,"%d\n", c1);
		//fprintf(out_file,"%d %d %d\n", c1, c2, c3);
	   }
	   */
	}

	fclose(ptr_file);
	return 0;
}