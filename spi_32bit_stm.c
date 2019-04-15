
// gcc -Wall -pthread -o spi_stm spi_32bit_stm.c -lpigpio
// sudo ./spin


#include <stdio.h>
#include <stdlib.h>
#include <time.h>
#include <pigpio.h>


int main(int argc, char **argv)
{
    if (gpioInitialise() < 0)
    {
	// pigpio initialisation failed.
    	
    }
    else
    {
        
    	// pigpio initialised okay.
   	printf("Pigpio intialized\n");
    }

    if (gpioHardwareClock(4,2000000) == 0){
	printf("Clock started\n");
    }

    int GPIOsetval = 0;
    GPIOsetval = gpioSetMode(17, PI_INPUT);
    //GPIOsetval = gpioSetMode(18, PI_INPUT);
    //GPIOsetval = gpioSetMode(19, PI_INPUT);
    //GPIOsetval = gpioSetMode(20, PI_INPUT);
    //GPIOsetval = gpioSetMode(21, PI_INPUT);
    //GPIOsetval = gpioSetMode(22, PI_INPUT);
    //GPIOsetval = gpioSetMode(23, PI_INPUT);
    //GPIOsetval = gpioSetMode(24, PI_INPUT);
    //GPIOsetval = gpioSetMode(25, PI_INPUT);

    //GPIOsetval = gpioSetMode(6, PI_OUTPUT);
    

    unsigned b_rate = 5000000; //20MHz maximum
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
    int spi_handle = spiOpen(1,b_rate,spi_flags);
    
    char tx[25600];
    char rx[25600];


    //char config[] = {0x00, 0x00, 0x00, 0x00}; // Data to send

    
    //char* buf = malloc(4*sizeof(char));
    
    for (int i = 0; i<25600; i++){
	tx[i] = 0x00;
    }
    int b_trans = spiXfer(spi_handle,tx,rx,25600);
    printf("Bytes transferred: %d\n",b_trans);

    for (int j = 0; j<25600; j=j+2){
	printf("%02X%02X ", rx[j], rx[j+1]);
	if ((j-62) % 64 == 0 && j != 0){
	   printf("\n");
	}

    }
    

    /*
    while (config[1] != 0xFF)
    {
        printf("Input SPI configuration (two hex numbers): ");
        scanf("%x %x %x %x", &config[0], &config[1], &config[2], &config[3]);

        printf("Sent to SPI: %02X %02X %02X %02X\n", config[0], config[1], config[2], config[3]);
        int b_trans = spiXfer(spi_handle,config,buf,4);
        // buf will now be filled with the data that was read from the slave
        printf("Bytes transferred: %d\n",b_trans);
        printf("Read from SPI: %02X %02X %02X %02X\n", buf[0], buf[1], buf[2], buf[3]);
    }    
    */    

    if (spiClose(spi_handle) == 0)
    {
	printf("SPI closed\n");
    	
    }
    if (gpioHardwareClock(4,0) == 0){
	printf("Clock stopped\n");
    }
    //free(buf);
    gpioTerminate();
    return 0;
}

