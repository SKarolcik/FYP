
// gcc -Wall -pthread -o pure_spi_stm pure_stm32.c -lpigpio
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
       //if (count == 0)
       //start = clock();
	    //uint32_t bits_read;
	    //printf("Interrupt happened at GPIO %d, at time %d\n",gpio,tick);
	    //bits_read = (gpioRead_Bits_0_31() & 0x03FC0000) >> 18;
	    //printf("ADC output: %04X\n; Count: %d", bits_read, count);
	    count += 1;
      if (count == 12799)
      {
	//clock_t end = clock();
        //double total = (double)(end - start)/CLOCKS_PER_SEC;
        //printf("Time difference: %f\n",total);
        count = 0;
        n_frames += 1;
      }
    }
}

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

    FILE *data_file;
    data_file = fopen("stm_readings.dat", "w");
    if (data_file == NULL){
        printf("Can't open the file\n");
        return 1;
    }

    unsigned b_rate = 100000;
    unsigned b_rate_stm32 = 8000000; //20MHz maximum
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

    char rx[25600];
    //char tx[25600];
    char addon[2];

    char config[] = {0x00, 0x00}; // Data to send
    char* buf = malloc(2*sizeof(char));
    
    
    
    int b_trans = spiRead(spi_handle_stm32,rx,25600);
    printf("Bytes transferred: %d\n",b_trans);

    for (int j = 0; j<25600; j=j+2){
	    printf("%02X%02X ", rx[j], rx[j+1]);
	    if ((j-62) % 64 == 0 && j != 0){
	        printf("\n");
	    }
    }
    
    //int b_trans1 = spiRead(spi_handle_stm32,addon,2);
    //rintf("Got another one %c; bytes: %d\n", addon[0], b_trans1);
    
    /*
    gpioISRFunc_t first_interrupt = &flash_int;
    
    if (gpioSetISRFunc(27,RISING_EDGE,0,first_interrupt)==0)
	{
	    printf("ISR registered on pin 17\n");
	}

    while (config[1] != 0xFF)
    {
        printf("Input SPI configuration (two hex numbers): ");
        scanf("%x %x", &config[0], &config[1]);

        printf("Sent to SPI: %02X %02X\n", config[0], config[1]);
        int b_trans = spiXfer(spi_handle,config,buf,2);
        // buf will now be filled with the data that was read from the slave
        printf("Bytes transferred: %d\n",b_trans);
        printf("Read from SPI: %02X %02X\n", buf[0], buf[1]);
    }    
   
    */
    if (spiClose(spi_handle_stm32) == 0)
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

