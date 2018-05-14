/*
 * Basic Linux Kernel module using GPIO interrupts.
 *
 * Author:
 * 	Interrupt handling part - Stefan Wendler (devnull@kaltpost.de)
 *  Device part :
 *     Copyright (C) 2013, Jack Whitham
 *     Copyright (C) 2009-2010, University of York
 *     Copyright (C) 2004-2006, Advanced Micro Devices, Inc.
 *
 *  Modified by Disk91 (www.disk91.com) for RFRPI Shield
 *
 * This software is licensed under the terms of the GNU General Public
 * License version 2, as published by the Free Software Foundation, and
 * may be copied, distributed, and modified under those terms.
 *
 * This program is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU General Public License for more details.
 *
 */
#include <linux/device.h>
#include <linux/miscdevice.h>
#include <linux/module.h>
#include <linux/kernel.h>
#include <linux/gpio.h>
#include <linux/interrupt.h>
#include <linux/time.h>
#include <linux/fs.h>
#include <linux/uaccess.h>

#define GPIO_FOR_RX_SIGNAL	17
#define GPIO_BIT0_ADC		18
#define GPIO_BIT1_ADC		19
#define GPIO_BIT2_ADC		20
#define GPIO_BIT3_ADC		21
#define GPIO_BIT4_ADC		22
#define GPIO_BIT5_ADC		23	
#define GPIO_BIT6_ADC		24
#define GPIO_BIT7_ADC		25
#define GPIO_BIT8_ADC		26
#define GPIO_BIT9_ADC		27
#define GPIO_BIT10_ADC		5
#define GPIO_BIT11_ADC		6
#define DEV_NAME 			"adccomms" 
#define BUFFER_SZ			1048576 

#define BCM2708_PERI_BASE       0x3F000000
#define GPIO_BASE               (BCM2708_PERI_BASE + 0x200000)	// GPIO controller  

#define INP_GPIO(g)   *(gpio.addr + ((g)/10)) &= ~(7<<(((g)%10)*3)) 
#define OUT_GPIO(g)   *(gpio.addr + ((g)/10)) |=  (1<<(((g)%10)*3)) //001
//alternative function
#define SET_GPIO_ALT(g,a) *(gpio.addr + (((g)/10))) |= (((a)<=3?(a) + 4:(a)==4?3:2)<<(((g)%10)*3))
 
#define GPIO_SET  *(gpio.addr + 7)  // sets   bits which are 1 ignores bits which are 0
#define GPIO_CLR  *(gpio.addr + 10) // clears bits which are 1 ignores bits which are 0
 
#define GPIO_READ(g)  *(gpio.addr + 13) &= (1<<(g))


static uint32_t pxValue[BUFFER_SZ];
static int  pRead;
static int  pWrite;
static int  wasOverflow;

static struct bcm2835_peripheral {
    unsigned long addr_p;
    int mem_fd;
    void *map;
    volatile unsigned int *addr;
};
 

static int map_peripheral(struct bcm2835_peripheral *p);
static void unmap_peripheral(struct bcm2835_peripheral *p);

static struct bcm2835_peripheral gpio_rd = {GPIO_BASE};

/* Define GPIOs for RX signal */
static struct gpio signals[] = {
		{ GPIO_FOR_RX_SIGNAL, GPIOF_IN, "RX Signal" },	// Rx signal
		{ GPIO_BIT0_ADC, GPIOF_IN, "Bit0 ADC" },
		{ GPIO_BIT1_ADC, GPIOF_IN, "Bit1 ADC" },
		{ GPIO_BIT2_ADC, GPIOF_IN, "Bit2 ADC" },
		{ GPIO_BIT3_ADC, GPIOF_IN, "Bit3 ADC" },
		{ GPIO_BIT4_ADC, GPIOF_IN, "Bit4 ADC" },
		{ GPIO_BIT5_ADC, GPIOF_IN, "Bit5 ADC" },
		{ GPIO_BIT6_ADC, GPIOF_IN, "Bit6 ADC" },
		{ GPIO_BIT7_ADC, GPIOF_IN, "Bit7 ADC" },
		{ GPIO_BIT8_ADC, GPIOF_IN, "Bit8 ADC" },
		{ GPIO_BIT9_ADC, GPIOF_IN, "Bit9 ADC" },
		{ GPIO_BIT10_ADC, GPIOF_IN, "Bit10 ADC" },
		{ GPIO_BIT11_ADC, GPIOF_IN, "Bit11 ADC" }
};

static int map_peripheral(struct bcm2835_peripheral *p)
{
	p->map = ioremap(GPIO_BASE, 41*4);
	p->addr=(uint32_t *)p->map; //41 GPIO register with 32 bit (4*8)
	if (p->addr != NULL){
	printk(KERN_INFO "Succesfully mapped GPIO port"); 
	}
   return 0;
}
 
static void unmap_peripheral(struct bcm2835_peripheral *p) {
 	iounmap(p->addr);//unmap the address
}


/* Later on, the assigned IRQ numbers for the buttons are stored here */
static int rx_irqs[] = { -1 };

/*
 * The interrupt service routine called on every pin status change
 */
static irqreturn_t rx_isr(int irq, void *data)
{

   	uint32_t curPx = 0;

	curPx = *(gpio_rd.addr + 13);
	curPx = (curPx & (0b11111111<<(18)))>>(18);
	
	pxValue[pWrite] = curPx;

	pWrite = ( pWrite + 1 )  & (BUFFER_SZ-1);
	if (pWrite == pRead) {
		// overflow
		pRead = ( pRead + 1 ) & (BUFFER_SZ-1);
		if ( wasOverflow == 0 ) {
	       printk(KERN_ERR "RFRPI - Buffer Overflow - IRQ will be missed");
	       wasOverflow = 1;
	    }
	} else {
		wasOverflow = 0;
	}
	return IRQ_HANDLED;
}


static int rx433_open(struct inode *inode, struct file *file)
{
    return nonseekable_open(inode, file);
}

static int rx433_release(struct inode *inode, struct file *file)
{
    return 0;
}

static ssize_t rx433_write(struct file *file, const char __user *buf,
                size_t count, loff_t *pos)
{
	return -EINVAL;
}

static ssize_t rx433_read(struct file *file, char __user *buf,
                size_t count, loff_t *pos)
{
	// returns one of the line with the time between two IRQs
	// return 0 : end of reading
	// return >0 : size
	// return -EFAULT : error
	char tmp[256];
	int _count;
	int _error_count;

	_count = 0;
	if ( pRead != pWrite ) {
		sprintf(tmp,"%03d\n",pxValue[pRead]);
  	    _count = strlen(tmp);
        _error_count = copy_to_user(buf,tmp,_count+1);
        if ( _error_count != 0 ) {
        	printk(KERN_ERR "RFRPI - Error writing to char device");
            return -EFAULT;
        }
		pRead = (pRead + 1) & (BUFFER_SZ-1);
	}
	return _count;
}

static struct file_operations rx433_fops = {
    .owner = THIS_MODULE,
    .open = rx433_open,
    .read = rx433_read,
    .write = rx433_write,
    .release = rx433_release,
};

static struct miscdevice rx433_misc_device = {
    .minor = MISC_DYNAMIC_MINOR,
    .name = DEV_NAME,
    .fops = &rx433_fops,
};



/*
 * Module init function
 */
static int __init adccomms_init(void)
{
	int ret = 0;
	printk(KERN_INFO "%s\n", __func__);

	// INITIALIZE IRQ TIME AND Queue Management
	//getnstimeofday(&lastIrq_time);
	pRead = 0;
	pWrite = 0;
	wasOverflow = 0;

	if(map_peripheral(&gpio_rd) == -1) 
	{
		printk(KERN_ALERT "Failed to map the physical GPIO registers into the virtual memory space.\n");
		return -1;
	}

	// register GPIO PIN in use
	ret = gpio_request_array(signals, ARRAY_SIZE(signals));

	if (ret) {
		printk(KERN_ERR "RFRPI - Unable to request GPIOs for RX Signals: %d\n", ret);
		goto fail2;
	}
	
	// Register IRQ for this GPIO
	ret = gpio_to_irq(signals[0].gpio);
	if(ret < 0) {
		printk(KERN_ERR "RFRPI - Unable to request IRQ: %d\n", ret);
		goto fail2;
	}
	rx_irqs[0] = ret;
	printk(KERN_INFO "RFRPI - Successfully requested RX IRQ # %d\n", rx_irqs[0]);
	ret = request_irq(rx_irqs[0], rx_isr, IRQF_TRIGGER_FALLING | 0, "rfrpi#rx", NULL);
	if(ret) {
		printk(KERN_ERR "RFRPI - Unable to request IRQ: %d\n", ret);
		goto fail3;
	}

	// Register a character device for communication with user space
    misc_register(&rx433_misc_device);

	return 0;

	// cleanup what has been setup so far
fail3:
	free_irq(rx_irqs[0], NULL);

fail2: 
	gpio_free_array(signals, ARRAY_SIZE(signals));
	return ret;	
}

/**
 * Module exit function
 */
static void __exit adccomms_exit(void)
{
	printk(KERN_INFO "%s\n", __func__);

    	misc_deregister(&rx433_misc_device);
	unmap_peripheral(&gpio_rd);

	// free irqs
	free_irq(rx_irqs[0], NULL);	
	
	// unregister
	gpio_free_array(signals, ARRAY_SIZE(signals));
}

MODULE_LICENSE("GPL");
MODULE_AUTHOR("Stefan Karolcik");
MODULE_DESCRIPTION("Linux Kernel Module for fast communication with parallel 12-bit ADC");

module_init(adccomms_init);
module_exit(adccomms_exit);