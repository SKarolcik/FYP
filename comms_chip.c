
// gcc -Wall -pthread -o chip_test comms_chip.c -lpigpio
// sudo ./spin


#include <stdio.h>
#include <stdlib.h>
#include <time.h>
#include <pigpio.h>

static volatile uint32_t count;
static volatile uint32_t n_frames;
static volatile clock_t start,end;

void flash_int(int gpio, int level, uint32_t tick)
{
    if (count < 12799)
    {
       if (count == 0)
       start = clock();
	    uint32_t bits_read;
	    //printf("Interrupt happened at GPIO %d, at time %d\n",gpio,tick);
	    bits_read = (gpioRead_Bits_0_31() & 0x03FC0000) >> 18;
	    //printf("ADC output: %04X\n; Count: %d", bits_read, count);
	    count += 1;
      if (count == 12799)
      {
	clock_t end = clock();
        double total = (double)(end - start)/CLOCKS_PER_SEC;
        printf("Time difference: %f\n",total);
        count = 0;
      }
    }
}

int main(int argc, char **argv)
{
    if (gpioInitialise() < 0)
    {
	// pigpio initialisation failed.
    	
    }
    else
    {
        count = 0;
    	// pigpio initialised okay.
   	printf("Pigpio intialized\n");
    }

    if (gpioHardwareClock(4,1000000) == 0){
	printf("Clock started\n");
    }

    int GPIOsetval = 0;
    GPIOsetval = gpioSetMode(17, PI_INPUT);
    GPIOsetval = gpioSetMode(18, PI_INPUT);
    GPIOsetval = gpioSetMode(19, PI_INPUT);
    GPIOsetval = gpioSetMode(20, PI_INPUT);
    GPIOsetval = gpioSetMode(21, PI_INPUT);
    GPIOsetval = gpioSetMode(22, PI_INPUT);
    GPIOsetval = gpioSetMode(23, PI_INPUT);
    GPIOsetval = gpioSetMode(24, PI_INPUT);
    GPIOsetval = gpioSetMode(25, PI_INPUT);

    GPIOsetval = gpioSetMode(6, PI_OUTPUT);
    

    unsigned b_rate = 32000; //20MHz maximum
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
    int spi_handle = spiOpen(0,b_rate,spi_flags);
    

    char config[] = {0x00, 0x00}; // Data to send
    //unsigned int tmp_conf[2];

    gpioISRFunc_t first_interrupt = &flash_int;
    
    if (gpioSetISRFunc(17,FALLING_EDGE,0,first_interrupt)==0)
	{
	    printf("ISR registered on pin 17\n");
	}
    
    char* buf = malloc(2*sizeof(char));
    

    while (config[1] != 0xFF)
    {
        printf("Input SPI configuration (two hex numbers): ");
        scanf("%x %x", &config[0], &config[1]);
        if (config[0] == 0x00){
        count = 0;}
        //config[0] = (char)tmp_conf[0];
        //config[1] = (char)tmp_conf[1];
        printf("Sent to SPI: %02X  %02X\n", config[0], config[1]);
        int b_trans = spiXfer(spi_handle,config,buf,2);
        // buf will now be filled with the data that was read from the slave
        printf("Bytes transferred: %d\n",b_trans);
        printf("Read from SPI: %02X  %02X\n", buf[0], buf[1]);
    }    
     


    if (spiClose(spi_handle) == 0)
    {
	printf("SPI closed\n");
    	
    }
    if (gpioHardwareClock(4,0) == 0){
	printf("Clock stopped\n");
    }
    free(buf);
    gpioTerminate();
    return 0;
}

