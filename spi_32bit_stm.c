
// gcc -Wall -pthread -o spi_stm spi_32bit_stm.c -lpigpio
// sudo ./spin


#include <stdio.h>
#include <stdlib.h>
#include <time.h>
#include <pigpio.h>
#include <unistd.h>


typedef struct Interrupt_dataset {
    FILE **file_p;
    int spi_stm32_h;
    volatile uint32_t count;
    char frame[25600];
    int * tmp;
}int_data;
//static volatile uint32_t count;
//static volatile uint32_t n_frames;
//static volatile clock_t start,end;

void print_into_file (FILE * fp, int b_trans, int count, char frame[25600]){
    if (b_trans != 25600){
        fprintf(fp, "Invalid frame no: %d (%d)\n\n", count, b_trans);
    }
    else{
        fprintf(fp, "Frame no: %d\n", count);
    }
    for (int j = 0; j<25600; j=j+2){
	    fprintf(fp, "%02X%02X ", frame[j], frame[j+1]);
	    if ((j-126) % 128 == 0 && j != 0){
	        fprintf(fp,"\n");
	    }
    }
}

void flash_int(int gpio, int level, uint32_t tick, void *userdata)
{
    clock_t start = clock();
    int_data* main_struct = (int_data*) userdata;
    int b_trans = spiRead(main_struct->spi_stm32_h,main_struct->frame,25600);
    //clock_t start = clock();
    //fprintf(*(main_struct->file_p), "Frame: %d, at\n", main_struct->count);
    print_into_file(*(main_struct->file_p), b_trans, (int)main_struct->count, main_struct->frame);
    (main_struct->count)++;
    clock_t end = clock();
    double total = (double)(end - start)/CLOCKS_PER_SEC;
    //printf("Time of interrupt function: %f\n", total);
}

/*
void write_and_print(void *struct_pointer){
    int_data* main_struct = (int_data *)struct_pointer;
    printf("Count value: %d\n", main_struct->count);

    printf("file_in = %d %d\n", main_struct->file_p, *(main_struct->file_p));
    //printf("tmp_in = %d %d\n", main_struct->tmp, *(main_struct->tmp));
    fprintf(*(main_struct->file_p), "Something written\n");
    
    (main_struct->count)++;

}
*/

int main(int argc, char **argv)
{
    if (gpioInitialise() < 0){
        printf("Can't initialize pigpio lib\n");
    }
    else{
   	    printf("Pigpio intialized\n");
    }

    if (gpioHardwareClock(4,2000000) == 0){
	    printf("Clock started\n");
    }

    int GPIOsetval = 0;
    GPIOsetval = gpioSetMode(27, PI_INPUT);
    if (GPIOsetval != 0){
        printf("Problem with setting int GPIO\n");
    }
    GPIOsetval = gpioSetMode(14, PI_OUTPUT);
    if (GPIOsetval != 0){
        printf("Problem with setting out GPIO\n");
    } 

    FILE *data_file = NULL;
    data_file = fopen("stm_readings.dat", "w");
    if (data_file == NULL){
        printf("Can't open the file\n");
        return 1;
    }
    //printf("original fp = %d\n",data_file);

    unsigned b_rate = 100000;
    unsigned b_rate_stm32 = 5000000; //20MHz maximum
    /* SPI configs - 22bits
        bbbbbb R T nnnn W A u2u1u0 p2p1p0 mm
        b - word size p to 32 bits
        R - 0(LSB MISO)
        T - 0(MSB MOSI)
	n - Ignored if W = 0
	W - 0(not 3 wire device)
	A - Standard SPI (0), Aux SPI (1)
	ux - Used chip select
	px - Polarity CS (low - 0)
	m - Mode POL, PHA
    */
    unsigned spi_flags = 0b0100000011110000000001;
    int spi_handle_stm32 = spiOpen(1,b_rate_stm32,spi_flags);
    int spi_handle = spiOpen(0,b_rate,spi_flags);

    //volatile char rx[25600];

    int_data int_struct;
    int_struct.file_p = &data_file;
    int_struct.spi_stm32_h = spi_handle_stm32;
    int_struct.count = 0;
    //for (int j = 0; j<25600; j++){
    //    int_struct.frame[j] = 0x00;
    //}

    
    int x = 256;
    int_struct.tmp = &x;
    
    //printf("file = %d %d\n", int_struct.file_p, *(int_struct.file_p));
    //printf("tmp = %d %d\n", int_struct.tmp, *(int_struct.tmp));

    char config[] = {0x00, 0x00}; // Data to send
    char* buf = malloc(2*sizeof(char));

    /*
    int b_trans = spiXfer(spi_handle,tx,rx,25600);
    printf("Bytes transferred: %d\n",b_trans);

    for (int j = 0; j<25600; j=j+2){
	    printf("%02X%02X ", rx[j], rx[j+1]);
	    if ((j-62) % 64 == 0 && j != 0){
	        printf("\n");
	    }
    }
    */
    gpioISRFuncEx_t first_interrupt = &flash_int;
    
    if (gpioSetISRFuncEx(27,RISING_EDGE,0,first_interrupt, &int_struct)==0)
	{
	    printf("ISR registered on pin 27\n");
	}

    while (count < 10)
    {
        printf("Input SPI configuration (two hex numbers): ");
        scanf("%x %x", &config[0], &config[1]);

        //printf("Sent to SPI: %02X %02X\n", config[0], config[1]);
        int b_trans = spiXfer(spi_handle,config,buf,2);
        if (config[1] == 0x00){
            gpioWrite(14, 1);
            usleep(10);
            gpioWrite(14, 0);
            //write_and_print(&int_struct);
        }
        // buf will now be filled with the data that was read from the slave
        //printf("Bytes transferred: %d\n",b_trans);
        //printf("Read from SPI: %02X %02X\n", buf[0], buf[1]);
    }    
   
    usleep(100);
    if (spiClose(spi_handle) == 0 && spiClose(spi_handle_stm32) == 0)
    {
	    printf("SPI closed\n");
    }
    if (gpioHardwareClock(4,0) == 0){
	printf("Clock stopped\n");
    }
    free(buf);
    fclose(data_file);
    gpioTerminate();
    return 0;
}

